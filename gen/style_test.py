"""Generates events once per style from gen/world/styles.json as drafts, all in parallel, and lays them out in one
labelled collage (a row per style, a column per event) in gen/drafts/. Nothing on the site changes.

    python3 -I gen/style_test.py <event-id> [<event-id> ...] [--styles "1 Eberron sourcebook,5 Gritty fantasy"]
        [--style-file <json of {label: style text}>]
"""
import concurrent.futures as cf
import json
import pathlib
import sys
import time

from PIL import Image as PILImage, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "gen"))
from image import generate, save_draft  # noqa: E402


def draft(event_id, style, **kw):
    err = ""
    for _ in range(3):
        try:
            return save_draft(generate(event_id, style=style, **kw))
        except SystemExit as e:
            err = str(e)
    return err


def collage(name, results, cols=5):
    """results: [(label, path or error)]; saved as gen/drafts/collage-<name>-<timestamp>.jpg."""
    w, h, label_h = 640, 357, 44
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 20)
    cols = min(len(results), cols)
    rows = -(-len(results) // cols)
    sheet = PILImage.new("RGB", (w * cols, (h + label_h) * rows), (20, 20, 20))
    draw = ImageDraw.Draw(sheet)
    for i, (label, result) in enumerate(results):
        x, y = (i % cols) * w, (i // cols) * (h + label_h)
        draw.text((x + 10, y + 11), label[:60], fill=(235, 235, 235), font=font)
        if isinstance(result, pathlib.Path):
            sheet.paste(PILImage.open(result).convert("RGB").resize((w, h)), (x, y + label_h))
        else:
            draw.text((x + 10, y + label_h + h // 2), "refused / failed", fill=(220, 90, 90), font=font)
    out = ROOT / "gen/drafts" / f"collage-{name}-{time.strftime('%Y%m%d-%H%M%S')}.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=85, optimize=True)
    return out


def main():
    args = sys.argv[1:]
    styles = json.loads((ROOT / "gen/world/styles.json").read_text())
    if "--style-file" in args:
        i = args.index("--style-file")
        styles = json.loads(pathlib.Path(args[i + 1]).read_text())
        args = args[:i] + args[i + 2:]
    if "--styles" in args:
        i = args.index("--styles")
        styles = {n: styles[n] for n in args[i + 1].split(",")}
        args = args[:i] + args[i + 2:]
    jobs = [(f"{event} | {name}", event, text) for name, text in styles.items() for event in args]
    with cf.ThreadPoolExecutor(len(jobs)) as pool:
        results = list(pool.map(lambda j: (j[0], draft(j[1], j[2])), jobs))
    for label, result in results:
        print(f"{label}: {result}")
    print("collage:", collage("styles", results, cols=5 if len(args) == 1 else len(args)))


if __name__ == "__main__":
    main()
