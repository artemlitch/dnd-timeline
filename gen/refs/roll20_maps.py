"""Downloads every Roll20 page's map image(s) into gen/refs/roll20/maps/ with an index.json.

Takes the map-layer images of each page (or its largest image when the page has no map layer), at original size.
Needs ~/projects/roll20-automation/r20.py set up for the "dnd" campaign.

    python3 -I gen/refs/roll20_maps.py
"""
import concurrent.futures as cf
import json
import pathlib
import re
import sys
import urllib.request

sys.path.insert(0, str(pathlib.Path.home() / "projects/roll20-automation"))
import r20

OUT = pathlib.Path(__file__).resolve().parent / "roll20" / "maps"


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def original(src):
    src = src.replace("https://s3.amazonaws.com/files.d20.io/", "https://files.d20.io/")
    return re.sub(r"/(thumb|med|max)\.(\w+)\?.*$", r"/original.\2", src)


def page_maps(page):
    g = r20.get(f"graphics/page/{page['id']}", "dnd") or {}
    imgs = [x for x in g.values() if isinstance(x, dict) and x.get("imgsrc") and not x.get("represents")]
    maps = [x for x in imgs if x.get("layer") == "map"]
    if not maps and imgs:
        maps = [max(imgs, key=lambda x: x.get("width", 0) * x.get("height", 0))]
    maps.sort(key=lambda x: -(x.get("width", 0) * x.get("height", 0)))
    files = []
    for i, m in enumerate(maps):
        url = original(m["imgsrc"])
        ext = url.rsplit(".", 1)[-1]
        name = f"{slug(page['name'] or page['id'])}{'' if i == 0 else f'-{i + 1}'}.{ext}"
        dest = OUT / name
        if not dest.exists():
            # some uploads have no original, only the sized copies
            for size in ("original", "max", "med"):
                req = urllib.request.Request(url.replace("/original.", f"/{size}."), headers={"User-Agent": "Mozilla/5.0"})
                try:
                    dest.write_bytes(urllib.request.urlopen(req, timeout=120).read())
                    break
                except Exception as e:
                    err = e
            else:
                print(f"FAIL {page['name']}: {url} {err}", flush=True)
                continue
        files.append({"file": name, "layer": m.get("layer"), "w": round(m.get("width", 0)), "h": round(m.get("height", 0))})
    return {"page": page["name"], "id": page["id"], "archived": page.get("archived", False), "maps": files}


OUT.mkdir(parents=True, exist_ok=True)
pages = r20.get("pages", "dnd")
with cf.ThreadPoolExecutor(8) as pool:
    index = sorted(pool.map(page_maps, pages.values()), key=lambda p: p["page"] or "")
(OUT / "index.json").write_text(json.dumps(index, indent=1) + "\n")
print(f"{len(index)} pages, {sum(len(p['maps']) for p in index)} map images")
