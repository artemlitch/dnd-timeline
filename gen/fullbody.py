"""Makes a full-body, to-scale reference of each named character from their portrait, gen/refs/fullbody/<slug>.jpg.

Heights come from gen/world/heights.json; cast_notes.json adds what the portrait can't show.

    python3 -I gen/fullbody.py Name [Name ...]
    python3 -I gen/fullbody.py --all     (every character in heights.json without a reference yet)
"""
import base64
import concurrent.futures as cf
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from image import ROOT, env, keep, post, small  # noqa: E402

OUT = ROOT / "gen/refs/fullbody"
PORTRAITS = json.loads((ROOT / "gen/regen/portraits.json").read_text())
NOTES = json.loads((ROOT / "gen/world/cast_notes.json").read_text())
HEIGHTS = json.loads((ROOT / "gen/world/heights.json").read_text())
STYLE = (ROOT / "gen/world/tone.txt").read_text().split("Style:", 1)[1].split("\n", 1)[0].strip()


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def make(name):
    prompt = (
        f"Full-body character reference of {name}, a fictional character from a tabletop fantasy game. "
        f"The attached image is {name}'s character art: match it exactly, the same face, hair, skin, build, outfit "
        f"and props, extending the outfit naturally to the whole body. {NOTES.get(name, '')} "
        f"{name} is {HEIGHTS[name]} tall. Show the whole figure from the top of the head to the feet, standing "
        f"straight in a relaxed neutral pose, facing the viewer, centred, filling the height of the frame, on a plain "
        f"flat light grey background. One figure only, nothing else in the image, no text. Style: {STYLE}")
    ref = small(ROOT / PORTRAITS[name]["file"])
    content = [{"type": "text", "text": prompt},
               {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(ref.read_bytes()).decode()}}]
    resp = post("https://openrouter.ai/api/v1/chat/completions",
                {"model": "google/gemini-3.1-flash-lite-image", "messages": [{"role": "user", "content": content}],
                 "modalities": ["image", "text"], "image_config": {"aspect_ratio": "2:3"}, "max_tokens": 4000},
                {"Authorization": "Bearer " + env("OPENROUTER_API_KEY")})
    imgs = (resp.get("choices") or [{}])[0].get("message", {}).get("images") or []
    if not imgs:
        return name, None, json.dumps(resp)[:200]
    out = OUT / f"{slug(name)}.jpg"
    keep(out)
    with tempfile.NamedTemporaryFile(suffix=".img") as tmp:
        tmp.write(base64.b64decode(imgs[0]["image_url"]["url"].split(",", 1)[1]))
        tmp.flush()
        subprocess.run(["sips", "-Z", "1024", "-s", "format", "jpeg", "-s", "formatOptions", "85", tmp.name, "--out", str(out)],
                       check=True, capture_output=True)
    return name, out, resp.get("usage", {}).get("cost")


def attempt(name):
    for _ in range(6):
        try:
            return make(name)
        except SystemExit as e:  # image.post exits on HTTP errors; credit held by in-flight requests clears
            err = str(e)
            if "in_flight" not in err:
                return name, None, err[:200]
            time.sleep(30)
    return name, None, "gave up"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    names = sys.argv[1:]
    if names == ["--all"]:
        names = [n for n in HEIGHTS if not (OUT / f"{slug(n)}.jpg").exists()]
    with cf.ThreadPoolExecutor(2) as pool:
        for name, out, info in pool.map(attempt, names):
            print(f"{name}: {out.relative_to(ROOT) if out else 'FAILED'} {info}", flush=True)


main()
