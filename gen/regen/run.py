"""Regenerates event images in the current house style, oldest images first, until the OpenRouter credit runs out.

Every event with a gen/prompts/ file is a candidate unless its current image was already made with the current
house style. Candidates are ordered by when their current image was made (first-batch images, with no date, come
first). Each image is saved as the event's next version by gen/image.py's generate_scene().

    python3 -I gen/regen/run.py [--limit N] [--threads 3] [--dry]
"""
import concurrent.futures as cf
import json
import pathlib
import sys
import threading
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "gen"))
from image import generate_scene, house_style  # noqa: E402


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def order():
    """Event ids to redo, oldest current image first."""
    style = house_style()
    events = json.loads((ROOT / "site/timeline.json").read_text())["events"]
    log = json.loads((ROOT / "gen/regen/versions.json").read_text())
    todo = []
    for ev in events:
        if not (ROOT / "gen/prompts" / f"{ev['id']}.prompt.txt").exists():
            continue
        current = next((v for v in reversed(log.get(ev["id"], [])) if v.get("version") == ev.get("img_version")), {})
        if current.get("style") == style:
            continue
        todo.append((current.get("at") or "", ev["id"]))
    return [eid for _, eid in sorted(todo)]


def main():
    todo = order()
    if "--limit" in sys.argv:
        todo = todo[: int(arg("--limit"))]
    print(f"{len(todo)} events to regenerate", flush=True)
    if "--dry" in sys.argv:
        print("\n".join(todo[:40]))
        return

    out_of_credit, lock = threading.Event(), threading.Lock()
    refused, failed = [], []

    def run(eid):
        for attempt in range(8):
            if out_of_credit.is_set():
                return eid, None
            try:
                return eid, generate_scene(eid)
            except (SystemExit, OSError) as e:  # OSError covers network timeouts
                err = str(e)
            if "in_flight" in err:
                time.sleep(30)  # credit held for unsettled requests, not spent
                continue
            if "HTTP 402" in err:
                out_of_credit.set()
                return eid, None
            if "content_filter" in err or "IMAGE_SAFETY" in err:
                if attempt < 1:
                    continue
                with lock:
                    refused.append(eid)
                return eid, None
            time.sleep(5 * (attempt + 1))
        with lock:
            failed.append(eid)
        return eid, None

    done = 0
    with cf.ThreadPoolExecutor(int(arg("--threads", 3))) as pool:
        for eid, out in pool.map(run, todo):
            if out:
                done += 1
                print(f"{done} {eid} -> {out.relative_to(ROOT)}", flush=True)
    print(f"FINISHED {done} regenerated" + (" (stopped: out of credit)" if out_of_credit.is_set() else "")
          + (f"; refused: {', '.join(refused)}" if refused else "") + (f"; failed: {', '.join(failed)}" if failed else ""),
          flush=True)


main()
