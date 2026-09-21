```python
import requests
import re
from pathlib import Path

OUTPUT = "pluto-brasil.m3u"

API_URL = (
    "https://service-channels.clusters.pluto.tv/v2/channels"
    "?appName=web"
    "&appVersion=5.0.0"
    "&deviceVersion=Chrome"
    "&deviceMake=Chrome"
    "&deviceModel=web"
    "&deviceType=web"
    "&deviceId=web"
    "&clientID=web"
    "&clientModelNumber=web"
    "&country=BR"
    "&language=pt-BR"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}


def slug(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def get_channels():
    response = requests.get(
        API_URL,
        headers=HEADERS,
        timeout=60
    )

    response.raise_for_status()

    data = response.json()

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        if isinstance(data.get("channels"), list):
            return data["channels"]

        for value in data.values():
            if isinstance(value, list):
                return value

    return []


def get_stream(channel):
    possible = [
        channel.get("stitched"),
        channel.get("streamUrl"),
        channel.get("stream_url"),
        channel.get("hlsUrl"),
        channel.get("hls_url"),
        channel.get("url"),
    ]

    for url in possible:
        if isinstance(url, str) and ".m3u8" in url:
            return url

    return None


def get_logo(channel):
    for key in [
        "logo",
        "logoUrl",
        "image",
        "imageUrl",
        "thumbnail"
    ]:
        value = channel.get(key)

        if isinstance(value, str):
            return value

    return ""


def main():

    print("Consultando Pluto TV Brasil...")

    channels = get_channels()

    if not channels:
        raise RuntimeError(
            "Nenhum canal foi encontrado."
        )

    playlist = [
        "#EXTM3U",
        ""
    ]

    total = 0

    for channel in channels:

        name = (
            channel.get("name")
            or channel.get("title")
            or channel.get("displayName")
            or "Pluto TV"
        )

        channel_id = (
            channel.get("id")
            or channel.get("channelId")
            or slug(name)
        )

        logo = get_logo(channel)
        stream = get_stream(channel)

        if not stream:
            continue

        name = name.replace('"', "'")

        playlist.append(
            f'#EXTINF:-1 '
            f'tvg-id="{channel_id}" '
            f'tvg-name="{name}" '
            f'tvg-logo="{logo}" '
            f'group-title="Pluto TV Brasil",'
            f'{name}'
        )

        playlist.append(stream)
        playlist.append("")

        total += 1

    if total == 0:
        raise RuntimeError(
            "A API respondeu, mas nenhum stream M3U8 foi encontrado."
        )

    Path(OUTPUT).write_text(
        "\n".join(playlist),
        encoding="utf-8"
    )

    print(
        f"Playlist criada com {total} canais."
    )

    print(
        f"Arquivo: {OUTPUT}"
    )


if __name__ == "__main__":
    main()
```
