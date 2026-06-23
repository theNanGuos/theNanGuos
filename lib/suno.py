import os
import time
import json
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.environ.get("KIE_BASE_URL", "https://api.kie.ai").rstrip("/")
API_KEY = os.environ["KIE_API_KEY"]



def gen_req(prompt: str) -> str:
    url = f"{BASE_URL}/api/v1/generate"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "prompt": prompt,
        "customMode": False,
        "instrumental": False,
        "model": "V4",
        "callBackUrl": "baidu.com"
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=60)

    print(resp.status_code)
    print(resp.text)

    resp.raise_for_status()

    data = resp.json()

    if data.get("code") != 200:
        raise RuntimeError(f"创建任务失败: {data}")

    task_id = data["data"]["taskId"]
    print(f"task_id: {task_id}")
    return task_id


def query_task(task_id: str) -> dict:
    url = f"{BASE_URL}/api/v1/generate/record-info"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
    }

    resp = requests.get(
        url,
        headers=headers,
        params={"taskId": task_id},
        timeout=60,
    )

    print(resp.status_code)
    print(resp.text)

    resp.raise_for_status()

    data = resp.json()

    if data.get("code") != 200:
        raise RuntimeError(f"查询任务失败: {data}")

    return data["data"]


def get_poll_interval(elapsed: float) -> int:
    if elapsed < 30:
        return 3
    elif elapsed < 120:
        return 8
    else:
        return 20


def wait_task(task_id: str, timeout_seconds: int = 15 * 60) -> dict:
    start = time.time()

    while True:
        task_info = query_task(task_id)

        state = task_info.get("status")
        print("当前状态:", state)

        state_lower = str(state).lower()

        if state_lower == "success":
            return task_info

        if state_lower == "fail":
            raise RuntimeError(f"生成失败: {task_info}")

        elapsed = time.time() - start

        if elapsed > timeout_seconds:
            raise TimeoutError(f"任务超时: {task_id}")

        interval = get_poll_interval(elapsed)
        print(f"{interval} 秒后继续轮询...")
        time.sleep(interval)


def extract_result_urls(task_info: dict) -> dict:
    songs = {}

    suno_data = task_info["response"]["sunoData"]
    for _, item in enumerate(suno_data):
        title = item["title"]
        url = item["audioUrl"]

        if title in songs:
            title = f"{title}"

        songs[title] = url

    return songs


def download_file(url: str, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)

    with requests.get(url, stream=True, timeout=120) as resp:
        resp.raise_for_status()

        with path.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


def download_results(songs: dict[str, str], output_dir: str = "works"):
    output_dir = Path(output_dir)

    for title, url in songs.items():
        path = output_dir / f"{title}.mp3"
        print(f"正在下载: {url}")
        download_file(url, path)
        print(f"已保存到: {path}")


def generate(prompt: str):

    task_id = gen_req(prompt)
    print("task_id:", task_id)

    task_info = wait_task(task_id)
    print("任务完成:", task_info)

    urls = extract_result_urls(task_info)

    if not urls:
        raise RuntimeError(f"没有找到下载链接: {task_info}")

    download_results(urls)
