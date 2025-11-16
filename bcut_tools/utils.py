import ffmpeg
import requests
import json

from bcut_tools.constants import HEADERS


def ffmpeg_render(media_file: str) -> bytes:
    "提取视频伴音并转码为aac格式"
    out, err = (
        ffmpeg.input(media_file, v="warning")
        .output("pipe:", ac=1, format="adts")
        .run(capture_stdout=True)
    )
    return out


def download_file(
    url: str,
    output_path: str,
    headers: dict = HEADERS,
) -> None:
    """下载文件并保存到指定路径"""
    resp = requests.get(url, headers=headers, stream=True)
    resp.raise_for_status()  # 如果请求失败，抛出异常
    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

def download_json(
    url: str,
    output_path: str,
    headers: dict = HEADERS,
) -> None:
    """下载JSON文件并保存到指定路径"""
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()  # 如果请求失败，抛出异常
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(resp.json(), f, ensure_ascii=False)