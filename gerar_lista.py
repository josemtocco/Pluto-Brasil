import uuid
from pathlib import Path
from urllib.parse import parse_qsl, urlencode
import requests

COUNTRY_IP = "177.47.27.205"
BOOT_URL = "https://boot.pluto.tv/v4/start"
CHANNELS_URL = "https://service-channels.clusters.pluto.tv/v2/guide/channels"
CATEGORIES_URL = "https://service-channels.clusters.pluto.tv/v2/guide/categories"
STITCHER_FALLBACK = "https://cfd-v4-service-channel-stitcher-use1-1.prd.pluto.tv"
APP_VERSION = "8.0.0-111b2b9dc00bd0bea9030b30662159ed9e7c8bc6"
DEVICE_VERSION = "122.0.0"
OUTPUT = Path(__file__).with_name("pluto-brasil.m3u")
TIMEOUT = 20

s = requests.Session()
s.headers.update({
    "Accept": "*/*",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Origin": "https://pluto.tv",
    "Referer": "https://pluto.tv/",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
})

def clean(v):
    return str(v or "").replace("\r"," ").replace("\n"," ").replace('"', "'").strip()

def boot():
    params = {
        "appName": "web",
        "appVersion": APP_VERSION,
        "deviceVersion": DEVICE_VERSION,
        "deviceModel": "web",
        "deviceMake": "chrome",
        "deviceType": "web",
        "clientID": str(uuid.uuid4()),
        "clientModelNumber": "1.0.0",
        "serverSideAds": "false",
        "drmCapabilities": "widevine:L3",
        "blockingMode": "",
    }
    r = s.get(BOOT_URL, params=params,
              headers={"X-Forwarded-For": COUNTRY_IP}, timeout=TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"Pluto boot HTTP {r.status_code}: {r.text[:500]}")
    data = r.json()
    token = data.get("sessionToken")
    if not token:
        raise RuntimeError("Pluto não retornou sessionToken.")
    return token, data.get("servers", {}).get("stitcher", STITCHER_FALLBACK), data.get("stitcherParams", "")

def auth_headers(token):
    return {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Authorization": f"Bearer {token}",
        "Origin": "https://pluto.tv",
        "Referer": "https://pluto.tv/",
        "User-Agent": s.headers["User-Agent"],
        "X-Forwarded-For": COUNTRY_IP,
    }

def channels(token):
    p = {"channelIds": "", "offset": "0", "limit": "1000", "sort": "number:asc"}
    r = s.get(CHANNELS_URL, params=p, headers=auth_headers(token), timeout=TIMEOUT)
    r.raise_for_status()
    ch = r.json().get("data", [])
    if not ch:
        raise RuntimeError("A Pluto não retornou canais.")
    cats = {}
    try:
        c = s.get(CATEGORIES_URL, params=p, headers=auth_headers(token), timeout=TIMEOUT)
        c.raise_for_status()
        for item in c.json().get("data", []):
            for cid in item.get("channelIDs", []):
                cats[cid] = item.get("name", "")
    except requests.RequestException:
        pass
    return ch, cats

def logo(ch):
    for img in ch.get("images") or []:
        if img.get("type") == "colorLogoPNG" and img.get("url"):
            return img["url"]
    for img in ch.get("images") or []:
        if img.get("url"):
            return img["url"]
    return ""

def stream_url(stitcher, token, stitcher_params, cid):
    p = {"jwt": token, "masterJWTPassthrough": "true", "includeExtendedEvents": "true"}
    if stitcher_params:
        p.update(dict(parse_qsl(stitcher_params.lstrip("?&"), keep_blank_values=True)))
    return f"{stitcher.rstrip('/')}/v2/stitch/hls/channel/{cid}/master.m3u8?{urlencode(p)}"

def main():
    print("Obtendo sessão Pluto TV Brasil...")
    token, stitcher, stitcher_params = boot()
    print("Obtendo canais...")
    chs, cats = channels(token)
    lines = ["#EXTM3U", "#PLAYLIST:Pluto TV Brasil"]
    n = 0
    for ch in chs:
        cid, name = ch.get("id"), clean(ch.get("name"))
        if not cid or not name:
            continue
        group = clean(cats.get(cid) or ch.get("category") or "Pluto TV")
        attrs = [f'tvg-id="{clean(cid)}"', f'tvg-name="{name}"']
        lg = clean(logo(ch))
        if lg:
            attrs.append(f'tvg-logo="{lg}"')
        attrs.append(f'group-title="{group}"')
        lines.append(f'#EXTINF:-1 {" ".join(attrs)},{name}')
        lines.append(stream_url(stitcher, token, stitcher_params, cid))
        n += 1
    if not n:
        raise RuntimeError("Nenhum canal foi incluído.")
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Playlist criada com {n} canais.")

if __name__ == "__main__":
    main()
