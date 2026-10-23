"""Tries variants of one event's prompt (each a list of (old, new) text replacements) across chosen styles, as drafts
in parallel, then lays them out in one labelled collage. Nothing on the site changes.

    python3 -I gen/variant_test.py <variants.json>

variants.json: {"event": id, "styles": [names from gen/world/styles.json], "variants": {label: [[old, new], ...]}}
"""
import concurrent.futures as cf
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "gen"))
from image import generate, save_draft  # noqa: E402
from style_test import collage  # noqa: E402


def main():
    spec = json.loads(pathlib.Path(sys.argv[1]).read_text())
    event = spec["event"]
    styles = json.loads((ROOT / "gen/world/styles.json").read_text())
    base = (ROOT / "gen/prompts" / f"{event}.prompt.txt").read_text()
    folder = ROOT / "gen/drafts" / event / "variants" / time.strftime("%Y%m%d-%H%M%S")
    folder.mkdir(parents=True, exist_ok=True)
    jobs = []
    for label, edits in spec["variants"].items():
        text = base
        for old, new in edits:
            assert old in text, f"{label}: {old[:60]!r} not in prompt"
            text = text.replace(old, new)
        path = folder / f"{label}.prompt.txt"
        path.write_text(text)
        jobs += [(f"{label} | {s}", path, styles[s]) for s in spec["styles"]]

    def run(job):
        name, path, style = job
        err = ""
        for _ in range(3):
            try:
                return name, save_draft(generate(event, style=style, prompt_file=path))
            except SystemExit as e:
                err = str(e)
        return name, err

    with cf.ThreadPoolExecutor(len(jobs)) as pool:
        results = list(pool.map(run, jobs))
    for name, result in results:
        print(f"{name}: {result}")
    print("collage:", collage(f"{event}-variants", results, cols=len(spec["styles"])))


if __name__ == "__main__":
    main()
