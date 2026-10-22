"""Generate images for every event that has no image file yet, 8 at a time, then record them in timeline.json.

usage: python3 -I gen/batch.py [--limit N]
"""
import concurrent.futures as cf, json, pathlib, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
data = json.loads((ROOT / "site/timeline.json").read_text())
todo = [e["id"] for e in data["events"] if e.get("kind") != "history" and not (ROOT / f"site/img/{e['id']}.jpg").exists()]
if "--limit" in sys.argv:
    todo = todo[: int(sys.argv[sys.argv.index("--limit") + 1])]
print(f"{len(todo)} to generate", flush=True)


def run(eid):
    for attempt in range(3):
        r = subprocess.run([sys.executable, "-I", str(ROOT / "gen/image.py"), eid, "--nojson"], capture_output=True, text=True)
        if r.returncode == 0:
            return eid, True, r.stdout.strip()
        if "402" in (r.stdout + r.stderr):
            return eid, False, "out of credit"
        time.sleep(5 * (attempt + 1))
    return eid, False, (r.stdout + r.stderr).strip()[-300:]


done = fail = 0
cost = 0.0
with cf.ThreadPoolExecutor(8) as pool:
    for eid, ok, msg in pool.map(run, todo):
        if ok:
            done += 1
            try:
                cost += float(msg.rsplit("cost=", 1)[1])
            except (IndexError, ValueError):
                pass
        else:
            fail += 1
            print(f"FAIL {eid}: {msg}", flush=True)
        if (done + fail) % 20 == 0:
            print(f"{done + fail}/{len(todo)} done, {fail} failed, ${cost:.2f}", flush=True)

# record every image file that now exists
data = json.loads((ROOT / "site/timeline.json").read_text())
for e in data["events"]:
    if e.get("kind") != "history" and (ROOT / f"site/img/{e['id']}.jpg").exists():
        e["img"] = f"img/{e['id']}.jpg"
(ROOT / "site/timeline.json").write_text(json.dumps(data, indent=2))
missing = [e["id"] for e in data["events"] if not e.get("img")]
print(f"FINISHED {done} ok, {fail} failed, ${cost:.2f}; events still without images: {len(missing)}", flush=True)
