#!/usr/bin/env python3
"""
Gera uma playlist M3U da Pluto TV Brasil.

Uso:
    python gerar_lista.py

A lista gerada é salva em:
    pluto-brasil.m3u

Atenção:
- A Pluto TV usa URLs HLS autenticadas/tokenizadas.
- O script obtém um token novo durante a execução.
- Não coloque tokens gerados manualmente no GitHub.
"""

import json
import uuid
from pathlib import Path
from urllib.parse import urlencode

import requests

COUNTRY = "br"
FORWARDED_IP = "177.47.27.205"

BOOT_URL = "https://boot.pluto.tv/v4/start"
CHANNELS_URL = "https://service-channels.clusters.pluto.tv/v2/guide/channels"

OUTPUT = Path(__file__).with_name("pluto-brasil.m3u")
TIMEOUT = 30

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/136.0 Safari/537.36",
})


def boot():
    device_id = uuid.uuid4().hex
    params = {
        "deviceVersion": "1",
        "deviceModel": "web",
        "deviceMake": "web",
        "deviceType": "web",
        "appVersion": "5.0.0",
        "clientID": device_id,
        "clientModelNumber": "1",
        "clientDeviceId": device_id,
        "deviceId": device_id,
        "country": COUNTRY.upper(),
        "language": "pt-BR",
    }

    headers = {
        "Origin": "https://pluto.tv",
        "Referer": "https://pluto.tv/",
        "X-Forwarded-For": FORWARDED_IP,
    }

    r = session.get(BOOT_URL, params=params, headers=headers, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()

    token = data.get("sessionToken")
    if not token:
        raise RuntimeError("A Pluto TV não retornou sessionToken.")

    stitcher = (
        data.get("servers", {}).get("stitcher")
        or "https://cfd-v4-service-channel-stitcher-use1-1.prd.pluto.tv"
    )
    stitcher_params = data.get("stitcherParams", "")

    return token, stitcher, stitcher_params


def get_channels(token):
    headers = {
        "Authorization": f"Bearer {token}",
        "Origin": "https://pluto.tv",
        "Referer": "https://pluto.tv/",
        "X-Forwarded-For": FORWARDED_IP,
    }

    params = {
        "channelIds": "",
        "offset": "0",
        "limit": "1000",
        "sort": "number:asc",
    }

    r = session.get(
        CHANNELS_URL,
        params=params,
        headers=headers,
        timeout=TIMEOUT,
    )
    r.raise_for_status()

    data = r.json().get("data", [])
    if not data:
        raise RuntimeError("Nenhum canal foi retornado pela API.")

    return data


def logo(channel):
    for image in channel.get("images", []):
        if image.get("type") in ("colorLogoPNG", "colorLogoSVG"):
            if image.get("url"):
                return image["url"]

    for image in channel.get("images", []):
        if image.get("url"):
            return image["url"]

    return ""


def stream_url(stitcher, token, stitcher_params, channel_id):
    params = {
        "jwt": token,
        "masterJWTPassthrough": "true",
    }

    # stitcherParams é fornecido pela própria Pluto no boot.
    if stitcher_params:
        for part in stitcher_params.lstrip("?&").split("&"):
            if "=" in part:
                key, value = part.split("=", 1)
                params[key] = value

    return (
        f"{stitcher.rstrip('/')}/v2/stitch/hls/channel/"
        f"{channel_id}/master.m3u8?{urlencode(params)}"
    )


def clean(value):
    return str(value or "").replace("\n", " ").replace("\r", " ").strip()


def main():
    token, stitcher, stitcher_params = boot()
    channels = get_channels(token)

    lines = [
        "#EXTM3U",
        "#PLAYLIST:Pluto TV Brasil",
    ]

    count = 0

    for ch in channels:
        channel_id = ch.get("id")
        name = clean(ch.get("name"))

        if not channel_id or not name:
            continue

        # Evita entradas sem numeração quando a API fornecer esse campo.
        number = ch.get("number", 0)
        if number is not None and str(number).strip() and str(number) != "0":
            display_name = f"{name}"
        else:
            display_name = name

        category = clean(ch.get("category") or "Pluto TV")
        logo_url = logo(ch)

        attributes = [
            f'tvg-id="{clean(channel_id)}"',
            f'tvg-name="{display_name}"',
        ]

        if logo_url:
            attributes.append(f'tvg-logo="{logo_url}"')

        attributes.append(f'group-title="{category}"')

        lines.append(
            f'#EXTINF:-1 {" ".join(attributes)},{display_name}'
        )
        lines.append(
            stream_url(stitcher, token, stitcher_params, channel_id)
        )
        count += 1

    if count == 0:
        raise RuntimeError("A lista final ficou sem canais.")

    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Playlist criada: {OUTPUT}")
    print(f"Canais: {count}")


if __name__ == "__main__":
    main()
