#!/usr/bin/env python3
"""usage: python3 -I generate.py <start> <end>  -- renders prompts.json[start:end] to jpg via OpenRouter."""
import base64
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
KEY = open(os.path.join(HERE, "key.txt")).read().strip()
URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "google/gemini-3.1-flash-lite-image"


REFS_DIR = os.path.join(HERE, "refs")


def load_refs():
    refs = []
    if not os.path.isdir(REFS_DIR):
        return refs
    for name in sorted(os.listdir(REFS_DIR)):
        stem, ext = os.path.splitext(name)
        if ext.lower() not in (".jpg", ".jpeg", ".png"):
            continue
        mime = "image/png" if ext.lower() == ".png" else "image/jpeg"
        with open(os.path.join(REFS_DIR, name), "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        refs.append((stem, "data:" + mime + ";base64," + b64))
    return refs


REFS = load_refs()


def build_content(prompt):
    matched = [(s, u) for s, u in REFS if s.lower() in prompt.lower()][:3]
    if not matched:
        return prompt
    names = ", ".join(s for s, _ in matched)
    text = ("Reference portraits attached, in order: " + names +
            ". Match these characters' faces, builds and outfits exactly. " + prompt)
    return [{"type": "text", "text": text}] + [
        {"type": "image_url", "image_url": {"url": u}} for _, u in matched]


def request_image(prompt):
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": build_content(prompt)}],
        "modalities": ["image", "text"],
        "image_config": {"aspect_ratio": "16:9"},
    }).encode()
    req = urllib.request.Request(URL, data=body, method="POST", headers={
        "Authorization": "Bearer " + KEY,
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.load(resp)
    url = data["choices"][0]["message"]["images"][0]["image_url"]["url"]
    header, b64 = url.split(",", 1)
    ext = ".png" if "png" in header else ".jpg"
    return base64.b64decode(b64), ext


def render(item):
    out = item["file"]
    if os.path.exists(out) and os.path.getsize(out) > 0:
        return item["id"], "skip", os.path.getsize(out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    last_err = "no image"
    for attempt in range(3):
        try:
            raw, ext = request_image(item["prompt"])
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                tmp.write(raw)
                tmp_path = tmp.name
            try:
                subprocess.run(
                    ["sips", "--resampleWidth", "1280", "-s", "format", "jpeg",
                     "-s", "formatOptions", "80", tmp_path, "--out", out],
                    check=True, capture_output=True)
            finally:
                os.unlink(tmp_path)
            size = os.path.getsize(out)
            if size > 0:
                return item["id"], "ok", size
            last_err = "empty output"
        except Exception as e:  # noqa: BLE001
            last_err = type(e).__name__ + ": " + str(e)[:200].replace(KEY, "***")
        time.sleep(5)
    return item["id"], "fail " + last_err, 0


def main():
    start, end = int(sys.argv[1]), int(sys.argv[2])
    with open(os.path.join(HERE, "prompts.json")) as f:
        items = json.load(f)[start:end]
    with ThreadPoolExecutor(4) as pool:
        for item_id, status, size in pool.map(render, items):
            print(item_id, status, size, flush=True)


if __name__ == "__main__":
    main()
