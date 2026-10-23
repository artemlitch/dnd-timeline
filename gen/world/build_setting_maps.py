"""Maps each Roll20 page (gen/refs/roll20/maps/index.json) to a setting and sub-location in settings.json.

Writes gen/world/setting_maps.json and a local review page, gen/world/setting_maps.html.
"name" = the page name says it outright; "guess" = inferred, needs checking.

    python3 -I gen/world/build_setting_maps.py
"""
import html
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
MAPS = ROOT / "gen/refs/roll20/maps"

# page name -> (setting id, sub-location id or None, confidence)
MAP = {
    "Library": ("narrator-library", None, "guess"),
    "Prison Gate": ("darkwood-prison", "gate-and-walls", "name"),
    "Prison Exterior 10ft squares": ("darkwood-prison", "prison-yard", "name"),
    "Prison Level 1": ("darkwood-prison", "cells-and-bunks", "name"),
    "Prison Level 2": ("darkwood-prison", "cells-and-bunks", "name"),
    "Prison Level 3": ("darkwood-prison", "cells-and-bunks", "name"),
    "Prison Basement": ("darkwood-prison", "secret-inventory-room", "guess"),
    "Dead Woods": ("darkwood-prison", None, "guess"),
    "Mara'bor Outside": ("marabor", None, "name"),
    "Mara'bor Inside": ("marabor", None, "name"),
    "Mine Entrance to Mara'bor": ("marabor", "mine-entrance", "name"),
    "Collapsed Mine": ("marabor", "mine-cart-ride", "guess"),
    "Necromancy Mine": ("marabor", None, "guess"),
    "Yedani Valley Airship Sabotage": ("yedani-mountains", "aundairian-valley-base", "name"),
    "Owlbear Cave": ("yedani-mountains", "owlbear-cave", "name"),
    "Military Outpost": ("yedani-mountains", "aundairian-valley-base", "guess"),
    "Kingsblade Overview": ("kingsblade", None, "name"),
    "Kingsblade Bridge": ("kingsblade", "bridge", "name"),
    "Kingsblade Crew Quarters": ("kingsblade", "crew-quarters-and-mess", "name"),
    "Kingsblade Hull": ("kingsblade", "engine-hull", "name"),
    "Kingsblade Lower Deck": ("kingsblade", "lower-deck-hangar-and-armory", "name"),
    "Kingsblade Main Deck": ("kingsblade", "main-deck", "name"),
    "Kingsblade War Room": ("kingsblade", "war-room", "name"),
    "Black Galifar Ship": ("kingsblade", None, "guess"),
    "Gold Galifar Ship": ("kingsblade", None, "guess"),
    "The Moonwatch": ("moonwatch", None, "name"),
    "The Moonwatch Attack": ("moonwatch", None, "name"),
    "Big Moonwatch": ("moonwatch", None, "name"),
    "Big Moonwatch Attack": ("moonwatch", None, "name"),
    "Main Deck Moonwatch": ("moonwatch", "flight-deck", "name"),
    "Small Main Deck Moonwatch": ("moonwatch", "flight-deck", "name"),
    "Below Deck Moonwatch": ("moonwatch", "lower-deck-and-storage", "name"),
    "Small Below Deck Moonwatch": ("moonwatch", "lower-deck-and-storage", "name"),
    "Crashed Moonwatch": ("moonwatch", None, "name"),
    "The Broadaxe": ("broadaxe", None, "name"),
    "Main Deck Broadaxe": ("broadaxe", None, "name"),
    "Below Deck Broadaxe": ("broadaxe", None, "name"),
    "Empyrean Main Deck": ("empyrean", None, "name"),
    "Empyrean Lower Deck": ("empyrean", None, "name"),
    "Empyrean Top Deck": ("empyrean", None, "name"),
    "Empyrean Dropship": ("empyrean", None, "name"),
    "Empyrean Tender Attack": ("empyrean", None, "name"),
    "Dogfight": ("skies-over-breland", None, "guess"),
    "Small Brelish Ship": ("skies-over-breland", "dagger-river-ambush", "guess"),
    "Wroat From The Air": ("wroat", None, "name"),
    "Wroat Street": ("wroat", "wroat-streets", "name"),
    "Wroat Military Police Station": ("wroat", "military-police-station", "name"),
    "Military Library": ("wroat", "wroat-military-library", "guess"),
    "Daily Grind": ("wroat", "daily-grind-and-bridge", "name"),
    "Exploding House": ("wroat", "gauss-hogs-house", "guess"),
    "Crime Scene House": ("wroat", "murphys-house", "guess"),
    "Hobbstweedle Village": ("hobbstweedle", None, "name"),
    "Air Field Hobbstweedle": ("hobbstweedle", "hobbstweedle-airfield", "name"),
    "Gelf, Elric & Screechs House": ("hobbstweedle", "gelf-elric-screech-house", "name"),
    "Clockworks Shop": ("hobbstweedle", "clockworks-shop", "name"),
    "Hobbstweedle Jail": ("hobbstweedle", "hobbstweedle-jail", "name"),
    "Hobbstweedle Library": ("hobbstweedle", "hobbstweedle-library", "name"),
    "Hobbstweedle Cemetery": ("hobbstweedle", "hobbstweedle-cemetery", "name"),
    "Brew & Ale": ("hobbstweedle", "brew-and-ale", "name"),
    "Brew & Ale Top Floor": ("hobbstweedle", "brew-and-ale", "name"),
    "Eloria and Eleanors House": ("hobbstweedle", "elorias-house", "name"),
    "Obstacle Course ": ("hobbstweedle", "obstacle-course", "name"),
    "Amphitheatre Day": ("hobbstweedle", "village-square-podium", "guess"),
    "Amphitheatre Night": ("hobbstweedle", "village-square-podium", "guess"),
    "Mansion Main Floor": ("blazehelms-mansion", None, "guess"),
    "Mansion Top Floor": ("blazehelms-mansion", None, "guess"),
    "Home Base": ("party-house", None, "guess"),
    "Boranex Forest Night": ("boranex-forest", "night-training-ground", "name"),
    "Demon Village": ("demon-village", "quasit-village", "name"),
    "Broken Portal": ("demon-village", "broken-circle", "guess"),
    "Imp Shack": ("demon-village", "old-imps-hut", "guess"),
    "Tomb of Centarrel 1": ("tomb-of-centarrel", None, "name"),
    "Tomb of Centarrel 2": ("tomb-of-centarrel", None, "name"),
    "Tomb of Centarrel 3": ("tomb-of-centarrel", None, "name"),
    "Ardev": ("ardev", None, "name"),
    "Ardev Attack": ("ardev", None, "name"),
    "Lower Ardev": ("ardev", "lower-ardev", "name"),
    "Lower Ardev Shifted": ("ardev", "lower-ardev", "name"),
    "Ardev Streets Day": ("ardev", "lower-ardev", "guess"),
    "Ardev Streets Night": ("ardev", "lower-ardev", "guess"),
    "Ardev Streets Night Attack": ("ardev", "lower-ardev", "guess"),
    "Ardev Graveyard": ("ardev", "ardev-cemetery", "name"),
    "Ardev Square": ("ardev", "ardev-square", "name"),
    "Ardev Plaza": ("ardev", "ardev-square", "guess"),
    "Ardev Plaza Attack": ("ardev", "ardev-square", "guess"),
    "Ardev Clocktower": ("ardev", "ardev-clocktower", "name"),
    "The Turckle and Churckle": ("ardev", "turckle-and-churckle", "name"),
    "Turckle Basement": ("ardev", "turckle-and-churckle", "name"),
    "Xal'ri House": ("ardev", "xalri-house", "name"),
    "Xal'ri Upstairs": ("ardev", "xalri-house", "name"),
    "Lireal Sr Den/Basement": ("ardev", "lirael-srs-den", "name"),
    "Lireal Sr Secret Office": ("ardev", "lirael-srs-den", "name"),
    "Kel House": ("ardev", "kel-house", "name"),
    "Kel Basement": ("ardev", "kel-house", "name"),
    "Kel Upstairs": ("ardev", "kel-house", "name"),
    "Kel Upstairs 2": ("ardev", "kel-house", "name"),
    "Silver Flame Church": ("ardev", "silver-flame-church", "name"),
    "Silver Flame Church Attack": ("ardev", "silver-flame-church", "name"),
    "Church Basement": ("ardev", "silver-flame-church", "guess"),
    "Ardev Library": ("ardev", "ardev-library", "name"),
    "Cannith Forge Ardev": ("ardev", "ardev-cannith-forge", "name"),
    "Cannith Forge Ardev Attack": ("ardev", "ardev-cannith-forge", "name"),
    "Cannith Top Floor": ("ardev", "ardev-cannith-forge", "name"),
    "Cannith Basement Recording": ("ardev", "ardev-cannith-forge", "name"),
    "Mercenary Castle": ("ardev", "ardev-castle", "guess"),
    "Castle Top Floor": ("ardev", "ardev-castle", "guess"),
    "Castle Dungeon": ("ardev", "ardev-castle", "guess"),
    "Fairgrounds": ("ardev", "ardev-fair-grounds", "name"),
    "Ardev Police Station": ("ardev", "ardev-police-station", "name"),
    "Ardev Police Station Attack": ("ardev", "ardev-police-station", "name"),
    "Ardev Police Basement": ("ardev", "ardev-police-station", "name"),
    "The Ardev Watch": ("ardev", "ardev-watch-office", "name"),
    "Valvier House": ("ardev", "valvier-house", "name"),
    "Valvier Basement": ("ardev", "valvier-house", "name"),
    "Abandoned House": ("ardev", "ardev-abandoned-house", "guess"),
    "Farks Bargain Whores": ("ardev", "farks-bargain-whores", "name"),
    "Gorgis House": ("ardev", None, "name"),
    "Gorgis Basement": ("ardev", None, "name"),
    "Unused Gorgis Basement": ("ardev", None, "name"),
    "Grimley House": ("ardev", None, "name"),
    "Grimley Basement": ("ardev", None, "name"),
    "Flowers House": ("ardev", None, "name"),
    "Flowers Top Floor": ("ardev", None, "name"),
    "Flowers Basement": ("ardev", None, "name"),
    "Threadwood House": ("ardev", None, "name"),
    "Threadwood Basement": ("ardev", None, "name"),
    "Free House": ("ardev", None, "guess"),
    "Free Basement 1": ("ardev", None, "guess"),
    "Mausoleum of Ardev": ("mausoleum-of-alton-ardev", None, "name"),
    "Stones Throw": ("stones-throw", None, "name"),
    "Secret Well": ("stones-throw", "stones-throw-well", "guess"),
    "Hearthsfire Forest": ("bears-wood", "hearthsfire-illusion", "guess"),
    "Hearthsfire": ("hearthsfire", None, "name"),
    "Emberfall Secret Meeting": ("hearthsfire", None, "guess"),
    "Starilaskur": ("starilaskur", None, "name"),
    "Starilaskur Attack": ("starilaskur", None, "name"),
    "Military Railway Junction": ("starilaskur", "railway-junction-underground-station", "name"),
    "Abandoned Train Station": ("starilaskur", "railway-junction-underground-station", "guess"),
    "Tunnel Lightning Rail 1": ("starilaskur", "railway-junction-underground-station", "guess"),
    "Tunnel Lightning Rail 2": ("starilaskur", "railway-junction-underground-station", "guess"),
    "Tunnel Lightning Rail 3": ("starilaskur", "railway-junction-underground-station", "guess"),
    "The Witchs Waltz": ("starilaskur", "witches-waltz", "name"),
    "EPTK Holding Cells": ("starilaskur", "eptf-headquarters", "guess"),
    "Military Police Jail": ("starilaskur", "starilaskur-police-station", "guess"),
    "Church of Onatar": ("starilaskur", "starilaskur-broadhelm-forge", "guess"),
    "Sayzia’s Elixir Emporium": ("starilaskur", None, "guess"),
    "Road Chase": ("even-hand-train", "armored-carriage", "guess"),
    "Lightning Rail 1": ("even-hand-train", "train-roof-and-underside", "name"),
    "Lightning Rail 2": ("even-hand-train", "train-roof-and-underside", "name"),
    "Lightning Rail 3": ("even-hand-train", "train-roof-and-underside", "name"),
    "Lightning Rail 4": ("even-hand-train", "train-roof-and-underside", "name"),
    "Inside Lightning Rail 1": ("even-hand-train", "train-car-interior", "name"),
    "Inside Lightning Rail 2": ("even-hand-train", "train-car-interior", "name"),
    "Inside  Lightning Rail 3": ("even-hand-train", "train-car-interior", "name"),
    "Inside Lightning Rail 4": ("even-hand-train", "train-car-interior", "name"),
    "Turtle Lightning Rail 4": ("even-hand-train", "train-head-elemental-ring", "guess"),
    "Inside Turtle Lightning Rail 4": ("even-hand-train", "train-car-interior", "guess"),
    "Mobile Fortress": ("even-hand-train", "turtle-fortress", "name"),
    "Astral Prison": ("even-hand-train", "astral-safe-portal", "guess"),
    "Dream Prison": ("dreamweaver-dream", "dream-prison", "name"),
    "Dreamweaver Eye": ("dreamweaver-dream", None, "name"),
    "Dream Office": ("dreamweaver-dream", None, "guess"),
    "Dream Training": ("dreamweaver-dream", None, "guess"),
    "Shadowmirror Cell ": ("mirror-nightmares", None, "guess"),
    "Morkoth Lair": ("bag-of-devouring", None, "guess"),
}


def main():
    settings = {s["id"]: s for s in json.loads((ROOT / "gen/world/settings.json").read_text())}
    pages = json.loads((MAPS / "index.json").read_text())
    names = {p["page"] for p in pages}
    missing = sorted(set(MAP) - names)
    assert not missing, f"mapped pages not in index.json: {missing}"
    for page, (sid, sub, _) in MAP.items():
        assert sid in settings, f"{page}: unknown setting {sid}"
        assert sub is None or any(x["id"] == sub for x in settings[sid]["sublocations"]), f"{page}: unknown sublocation {sub}"

    out = [{"page": p["page"], "setting": MAP[p["page"]][0], "sublocation": MAP[p["page"]][1],
            "confidence": MAP[p["page"]][2], "files": [m["file"] for m in p["maps"]]}
           for p in pages if p["page"] in MAP]
    (ROOT / "gen/world/setting_maps.json").write_text(json.dumps(out, indent=1) + "\n")
    unmapped = [p for p in pages if p["page"] not in MAP]
    (ROOT / "gen/world/setting_maps.html").write_text(render(settings, out, unmapped))
    print(f"{len(out)} pages mapped ({sum(o['confidence'] == 'guess' for o in out)} guesses), {len(unmapped)} unmapped")


def thumb(file):
    return f"../refs/roll20/maps/thumbs/{pathlib.Path(file).stem}.jpg"


def card(p, label, guess):
    files = p.get("files") or [m["file"] for m in p["maps"]]
    imgs = "".join(f'<a href="../refs/roll20/maps/{html.escape(f)}" target="_blank"><img loading="lazy" src="{thumb(f)}"></a>'
                   for f in files[:4])
    more = f'<span class="more">+{len(files) - 4} more</span>' if len(files) > 4 else ""
    return (f'<figure class="{"guess" if guess else ""}"><div class="imgs">{imgs}{more}</div>'
            f'<figcaption><b>{html.escape(p["page"])}</b>{label}</figcaption></figure>')


def render(settings, out, unmapped):
    body = []
    for sid, s in settings.items():
        rows = [o for o in out if o["setting"] == sid]
        subs = {x["id"]: x["name"] for x in s["sublocations"]}
        cards = "".join(card(o, f'<span class="sub">{html.escape(subs.get(o["sublocation"], "whole setting"))}</span>'
                                + ('<span class="tag">guess</span>' if o["confidence"] == "guess" else ""), o["confidence"] == "guess")
                        for o in sorted(rows, key=lambda o: (o["sublocation"] or "", o["page"])))
        empty = [n for i, n in subs.items() if not any(o["sublocation"] == i for o in rows)]
        body.append(f'<section><h2>{html.escape(s["name"])} <small>{sid} · {len(rows)} maps</small></h2>'
                    + (f'<div class="grid">{cards}</div>' if rows else '<p class="none">No Roll20 map.</p>')
                    + (f'<p class="empty">Sub-locations with no map: {html.escape(", ".join(empty))}</p>' if empty else "")
                    + "</section>")
    body.append(f'<section><h2>Not matched to any setting <small>{len(unmapped)} maps</small></h2><div class="grid">'
                + "".join(card(p, "", False) for p in unmapped) + "</div></section>")
    return f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Setting Maps</title><style>
:root{{--bg:#16130f;--fg:#ece4d6;--mut:#a59a88;--card:#221d17;--brass:#c9a35a;--warn:#d9822b}}
body{{margin:0;padding:24px 16px 80px;background:var(--bg);color:var(--fg);font:15px/1.4 system-ui,sans-serif}}
h1{{color:var(--brass);margin:0 0 4px}} p.lead{{color:var(--mut);margin:0 0 24px}}
section{{margin:0 0 36px}} h2{{color:var(--brass);border-bottom:1px solid #3a3128;padding-bottom:6px}}
h2 small{{color:var(--mut);font-weight:400;font-size:13px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:14px}}
figure{{margin:0;background:var(--card);border-radius:8px;overflow:hidden;border:1px solid #2e2720}}
figure.guess{{border-color:var(--warn)}}
.imgs{{display:flex;flex-wrap:wrap;background:#000;position:relative}} .imgs a{{flex:1 1 50%}}
.imgs img{{width:100%;height:150px;object-fit:cover;display:block}}
.more{{position:absolute;right:6px;bottom:6px;background:#000c;padding:2px 6px;border-radius:4px;font-size:12px}}
figcaption{{padding:8px 10px;display:flex;flex-direction:column;gap:2px}} .sub{{color:var(--mut);font-size:13px}}
.tag{{color:var(--warn);font-size:12px;font-weight:600;text-transform:uppercase}}
.none,.empty{{color:var(--mut);font-size:13px}}
</style></head><body><h1>Setting maps</h1>
<p class="lead">Every Roll20 page matched to a setting in gen/world/settings.json. Orange = a guess from the page name, check it. Click a thumbnail for the full map.</p>
{"".join(body)}</body></html>
"""


main()
