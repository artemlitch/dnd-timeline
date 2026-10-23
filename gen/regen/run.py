"""Regenerates event images from their prompt files in gen/prompts/, most important characters first.

Skips events whose portraits are only the three player characters. Orders the rest by their most-mentioned NPC
(event count in list.json's npc_roster, else in sources.json), then by the sum over all their NPCs. Each image is
written as the event's next version by gen/image.py. Runs until the OpenRouter credit is gone; events already made
from a gen/prompts/ file (per gen/regen/versions.json) are skipped, so a rerun picks up where it stopped; --since
<timestamp> skips only those made at or after it, to redo older ones.

    python3 -I gen/regen/run.py [--since 2026-10-23T10:50] [--limit N] [--dry]
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
PROMPTS = ROOT / 'gen' / 'prompts'
PCS = {'Lirael', 'Brand', 'Sazed'}


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def order():
    """Event ids with NPC portraits, most important characters first."""
    sources = json.loads((HERE / 'sources.json').read_text())
    roster = {r['name']: r['events'] for r in json.loads((HERE / 'list.json').read_text())['npc_roster']}
    seen = Counter(r['name'] for s in sources for r in s['refs'] if r['name'] not in PCS)
    weight = lambda n: roster.get(n, seen[n])
    ranked = []
    for s in sources:
        npcs = [r['name'] for r in s['refs'] if r['name'] not in PCS]
        if npcs:
            ranked.append((-max(weight(n) for n in npcs), -sum(weight(n) for n in npcs), s['id']))
    return [eid for *_, eid in sorted(ranked)]


def main():
    log = json.loads((HERE / 'versions.json').read_text())
    since = arg('--since', '')
    done = {eid for eid, vs in log.items()
            if any((v.get('prompt') or '').startswith('gen/prompts/') and (v.get('at') or '') >= since for v in vs)}
    todo = [eid for eid in order() if eid not in done and (PROMPTS / f'{eid}.prompt.txt').exists()]
    if '--limit' in sys.argv:
        todo = todo[: int(arg('--limit'))]
    print(f'{len(todo)} events to regenerate', flush=True)
    if '--dry' in sys.argv:
        print('\n'.join(todo[:40]))
        return

    lock, out_of_credit = threading.Lock(), threading.Event()
    refused = []

    def run(eid):
        if out_of_credit.is_set():
            return eid, None
        for attempt in range(8):
            r = subprocess.run([sys.executable, '-I', str(ROOT / 'gen/image.py'), eid], capture_output=True, text=True)
            out = (r.stdout + r.stderr).strip()
            if r.returncode == 0:
                tail = out.rsplit('cost=', 1)[1]
                return eid, float(tail) if tail != 'None' else 0.0
            if 'in_flight' in out:
                # credit held for unsettled requests, not spent: wait for it to settle
                time.sleep(30)
                continue
            if 'HTTP 402' in out:
                out_of_credit.set()
                return eid, None
            if 'content_filter' in out or 'IMAGE_SAFETY' in out:
                with lock:
                    refused.append(eid)
                print(f'REFUSED {eid}', flush=True)
                return eid, None
            time.sleep(5 * (attempt + 1))
        print(f'FAIL {eid}: {out[-300:]}', flush=True)
        return eid, None

    spent, ok = 0.0, 0
    with cf.ThreadPoolExecutor(int(arg('--threads', 3))) as pool:
        for n, (eid, cost) in enumerate(pool.map(run, todo), 1):
            if cost is not None:
                ok += 1
                spent += cost
            if n % 10 == 0:
                print(f'{n}/{len(todo)} processed, {ok} regenerated, ${spent:.2f}', flush=True)
    print(f'FINISHED {ok} regenerated, ${spent:.2f}' + (' (stopped: out of credit)' if out_of_credit.is_set() else '')
          + (f'; refused: {", ".join(refused)}' if refused else ''), flush=True)


main()
