"""Turns each ship's top-down Roll20 token (gen/world/ships.json) into a three-quarter side-view concept image,
gen/refs/ships/<slug>.jpg, to use as the ship's reference in event prompts. The Moonwatch concept is attached as an
example of the camera angle, so make that one first.

    python3 -I gen/ship_concepts.py [Ship Name ...]
"""
import base64
import concurrent.futures as cf
import json
import pathlib
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from image import ROOT, env, keep, post, small  # noqa: E402

MODEL = "google/gemini-3.1-flash-lite-image"
OUT = ROOT / "gen/refs/ships"


def concept(name, ship):
    prompt = (
        f"Detailed concept painting of a single airship from a Dungeons & Dragons campaign set in Eberron: {name}.\n"
        "The FIRST attached image is a flat top-down game token of this exact ship, seen from directly above. It is a "
        "design sketch only. Rebuild the ship as a solid three-dimensional vessel and show it from the SIDE: the camera "
        "is level with the ship, slightly below it, looking at its flank in a three-quarter side view, so the side of "
        "the hull, its keel and underside, and its height are clearly visible. Do NOT show it from above and do not "
        "copy the token's angle. The whole ship in frame from bow to stern, flying, with clear sky around it. Keep every "
        "part of the token's design, colours and proportions.\n"
        "The SECOND attached image is a different ship, attached only as an example of the camera angle to use. Do not "
        "copy anything else from it.\n"
        f"The ship: {ship['look']}\n"
        "Wide 16:9 composition. No people needed. No text, lettering, captions or watermarks.")
    content = [{"type": "text", "text": prompt}]
    for ref in (small(ROOT / ship["file"]), OUT / "the-moonwatch.jpg"):
        content.append({"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(ref.read_bytes()).decode()}})
    resp = post("https://openrouter.ai/api/v1/chat/completions",
                {"model": MODEL, "messages": [{"role": "user", "content": content}], "modalities": ["image", "text"],
                 "image_config": {"aspect_ratio": "16:9"}},
                {"Authorization": "Bearer " + env("OPENROUTER_API_KEY")})
    imgs = (resp.get("choices") or [{}])[0].get("message", {}).get("images") or []
    if not imgs:
        return name, None, json.dumps(resp)[:300]
    out = OUT / (re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") + ".jpg")
    keep(out)
    with tempfile.NamedTemporaryFile(suffix=".img") as tmp:
        tmp.write(base64.b64decode(imgs[0]["image_url"]["url"].split(",", 1)[1]))
        tmp.flush()
        subprocess.run(["sips", "--resampleWidth", "1280", "-s", "format", "jpeg", "-s", "formatOptions", "85",
                        tmp.name, "--out", str(out)], check=True, capture_output=True)
    return name, out, resp.get("usage", {}).get("cost")


def main():
    ships = json.loads((ROOT / "gen/world/ships.json").read_text())
    names = sys.argv[1:] or list(ships)
    OUT.mkdir(parents=True, exist_ok=True)
    with cf.ThreadPoolExecutor(6) as pool:
        for name, out, info in pool.map(lambda n: concept(n, ships[n]), names):
            print(f"{name}: {out.relative_to(ROOT) if out else 'FAILED'} {info}")


main()
