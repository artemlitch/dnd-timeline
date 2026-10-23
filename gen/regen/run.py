"""Regenerates event images with every character portrait attached, most important characters first.

Skips events whose portraits are only the three player characters. Orders the rest by their most-mentioned NPC
(event count in list.json's npc_roster, else in sources.json), then by the sum over all their NPCs. Runs until
the OpenRouter credit is gone and logs each finished event to gen/regen/done.json, so a rerun picks up where it
stopped.

    python3 -I gen/regen/run.py [--limit N] [--dry]
"""
import concurrent.futures as cf
import json
import pathlib
import subprocess
import sys
import threading
import time
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = ROOT / 'gen' / 'regen'
PCS = {'Lirael', 'Brand', 'Sazed'}

sources = json.loads((HERE / 'sources.json').read_text())
roster = {r['name']: r['events'] for r in json.loads((HERE / 'list.json').read_text())['npc_roster']}
seen = Counter(r['name'] for s in sources for r in s['refs'] if r['name'] not in PCS)
weight = lambda n: roster.get(n, seen[n])

done_path = HERE / 'done.json'
done = json.loads(done_path.read_text()) if done_path.exists() else {}

todo = []
for s in sources:
    npcs = [r['name'] for r in s['refs'] if r['name'] not in PCS]
    if npcs and s['id'] not in done:
        todo.append((max(weight(n) for n in npcs), sum(weight(n) for n in npcs), s['id'], npcs, len(s['refs'])))
todo.sort(key=lambda t: (-t[0], -t[1], t[2]))
if '--limit' in sys.argv:
    todo = todo[: int(sys.argv[sys.argv.index('--limit') + 1])]
print(f'{len(todo)} events to regenerate', flush=True)
if '--dry' in sys.argv:
    for t in todo[:40]:
        print(t)
    sys.exit()

lock, out_of_credit = threading.Lock(), threading.Event()


def run(item):
    eid = item[2]
    if out_of_credit.is_set():
        return eid, None
    for attempt in range(3):
        r = subprocess.run([sys.executable, '-I', str(ROOT / 'gen/image.py'), eid, '--nojson', '--sources'],
                           capture_output=True, text=True)
        out = (r.stdout + r.stderr).strip()
        if r.returncode == 0:
            cost = float(out.rsplit('cost=', 1)[1]) if 'cost=' in out and out.rsplit('cost=', 1)[1] != 'None' else 0.0
            with lock:
                done[eid] = {'cost': cost, 'refs': item[4], 'at': time.strftime('%Y-%m-%dT%H:%M:%S')}
                done_path.write_text(json.dumps(done, indent=1) + '\n')
            return eid, cost
        if 'HTTP 402' in out:
            out_of_credit.set()
            return eid, None
        time.sleep(5 * (attempt + 1))
    print(f'FAIL {eid}: {out[-300:]}', flush=True)
    return eid, None


spent, ok = 0.0, 0
with cf.ThreadPoolExecutor(6) as pool:
    for n, (eid, cost) in enumerate(pool.map(run, todo), 1):
        if cost is not None:
            ok += 1
            spent += cost
        if n % 10 == 0:
            print(f'{n}/{len(todo)} processed, {ok} regenerated, ${spent:.2f}', flush=True)
print(f'FINISHED {ok} regenerated, ${spent:.2f}' + (' (stopped: out of credit)' if out_of_credit.is_set() else ''), flush=True)
