"""Builds gen/regen/sources.json: every event to regenerate with the portrait files of the characters in it.

Reads list.json (events and the characters in each) and portraits.json (character name -> portrait file).
Fails if a character has no entry in portraits.json or a mapped file is missing.

    python3 -I gen/regen/build_sources.py
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = ROOT / 'gen' / 'regen'

regen = json.loads((HERE / 'list.json').read_text())
portraits = json.loads((HERE / 'portraits.json').read_text())
timeline = {e['id']: e for e in json.loads((ROOT / 'site' / 'timeline.json').read_text())['events']}

# list.json only names the NPCs in most events; the player characters come in the way gen/image.py finds them
PCS = ['Lirael', 'Brand', 'Sazed']
def pcs_in(eid):
    ev = timeline[eid]
    text = ' '.join([ev['title'], ev.get('summary', ''), ev.get('detail', ''), ' '.join(ev.get('tags', []))]).lower()
    return [n for n in PCS if n.lower() in text]

problems = []
for name, p in portraits.items():
    if p['file'] and not (ROOT / p['file']).is_file():
        problems.append(f'{name}: {p["file"]} does not exist')

people = {}
for e in regen['wrong_batch1']:
    people.setdefault(e['id'], {'title': e['title'], 'session': e['session'], 'names': []})['names'] += e['characters']
for e in regen['npc_major']:
    people.setdefault(e['id'], {'title': e['title'], 'session': e['session'], 'names': []})['names'] += e['npcs']

events = []
for eid in regen['all_to_regenerate']:
    e = people[eid]
    names = list(dict.fromkeys(pcs_in(eid) + e['names']))
    for n in names:
        if n not in portraits:
            problems.append(f'{eid}: no portraits.json entry for {n}')
    refs = [{'name': n, 'file': portraits[n]['file']} for n in names if n in portraits and portraits[n]['file']]
    missing = [n for n in names if n in portraits and not portraits[n]['file']]
    events.append({'id': eid, 'title': e['title'], 'session': e['session'], 'refs': refs, 'no_portrait': missing})

if problems:
    sys.exit('\n'.join(problems))

(HERE / 'sources.json').write_text(json.dumps(events, indent=1, ensure_ascii=False) + '\n')
print(f'{len(events)} events, {sum(len(e["refs"]) for e in events)} portrait references, '
      f'{sum(1 for e in events if e["no_portrait"])} events with a character who has no portrait')
