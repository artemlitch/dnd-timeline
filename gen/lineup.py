"""Builds one to-scale lineup image of any number of characters from their full-body references
(gen/refs/fullbody/), each labelled with their name. Long lists wrap into rows on the same scale.

    python3 -I gen/lineup.py out.jpg Name [Name ...]
"""
import json
import pathlib
import re
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
HEIGHTS = json.loads((ROOT / "gen/world/heights.json").read_text())
TALLEST_PX = 900
PER_ROW = 14
MAX_WIDTH = 2400


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def inches(h):
    m = re.match(r"(\d+) f(?:ee|oo)t(?: (\d+) inch)?", h)
    return int(m.group(1)) * 12 + int(m.group(2) or 0)


def figure(path):
    """The reference cropped to the figure: rows and columns that differ from the plain background."""
    im = Image.open(path).convert("RGB")
    bg = im.getpixel((5, 5))
    mask = Image.eval(im.convert("L"), lambda v: 255 if abs(v - sum(bg) / 3) > 18 else 0)
    box = mask.getbbox() or (0, 0, im.width, im.height)
    return im.crop(box)


def build(out, names, labels=True):
    tallest = max(inches(HEIGHTS[n]) for n in names)
    figs = []
    for n in names:
        im = figure(ROOT / "gen/refs/fullbody" / f"{slug(n)}.jpg")
        h = round(TALLEST_PX * inches(HEIGHTS[n]) / tallest)
        figs.append((n, im.resize((round(im.width * h / im.height), h))))
    rows = [figs[i:i + PER_ROW] for i in range(0, len(figs), PER_ROW)]
    gap, label_h, top = 40, 70, 40
    row_h = top + TALLEST_PX + label_h
    width = max(sum(f.width for _, f in row) + gap * (len(row) + 1) for row in rows)
    sheet = Image.new("RGB", (width, row_h * len(rows)), (235, 235, 235))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 34)
    except OSError:
        font = ImageFont.load_default()
    for r, row in enumerate(rows):
        x, floor = gap, r * row_h + top + TALLEST_PX
        for n, f in row:
            sheet.paste(f, (x, floor - f.height))
            if labels:
                tw = draw.textlength(n, font=font)
                draw.text((x + (f.width - tw) / 2, floor + 15), n, fill=(20, 20, 20), font=font)
            x += f.width + gap
        draw.line([(0, floor), (width, floor)], fill=(150, 150, 150), width=3)
    if sheet.width > MAX_WIDTH:
        sheet = sheet.resize((MAX_WIDTH, round(sheet.height * MAX_WIDTH / sheet.width)), Image.LANCZOS)
    sheet.save(out, quality=82, optimize=True)


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2:])
