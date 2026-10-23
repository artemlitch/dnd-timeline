"""Scene images for timeline events, built from gen/prompts/<event-id>.prompt.txt.

Generating an image and saving it are separate steps:
  generate(event_id, ...)      -> Image: the picture plus everything about how it was made; saves nothing
  save_draft(image)            -> gen/drafts/<event-id>/<timestamp>.jpg + .json; site untouched, safe in parallel
  save_version(image)          -> site/img/<event-id>.v<N>.jpg as the event's next version, logged in
                                  gen/regen/versions.json; the previous site image moves to gen/test/old/
  generate_scene(event_id,...) -> save_version(generate(...)), the canonical way to make a scene image

usage: python3 -I gen/image.py <event-id> [--style <text>] [--no-lineup] [--model <id>] [--draft] [--print]
  --style overrides the Style line of gen/world/tone.txt; --no-lineup attaches separate portraits instead of the
  to-scale character outline; --draft saves a draft instead of a version; --print shows the finished prompt and
  generates nothing.

Prompt placeholders: {tone} (gen/world/tone.txt), {setting:<id>[/<sub-id>]} (gen/world/settings.json as it looks at
the event's session), {cast:Name} (gen/world/cast.json), {framing:<epic|wide|medium|close>} (gen/world/framing.json),
{maps:Page|Page#2} (attaches Roll20 maps) and {references}.
"""
import base64, dataclasses, fcntl, json, pathlib, re, subprocess, sys, tempfile, time, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODEL = "google/gemini-3.1-flash-lite-image"
SHIPS = json.loads((ROOT / "gen/world/ships.json").read_text())
PORTRAITS = json.loads((ROOT / "gen/regen/portraits.json").read_text()) | SHIPS
# every character gets their full description; one with no cast.json entry falls back to their portrait
_NOTES = json.loads((ROOT / "gen/world/cast_notes.json").read_text())
CAST = {name.lower(): f"{name}: draw from the reference portrait." + (f" {_NOTES[name]}" if name in _NOTES else "")
        for name, p in PORTRAITS.items() if name not in SHIPS and (p or {}).get("file")}
CAST.update({name.lower(): f"{name}: {text}" for name, text in json.loads((ROOT / "gen/world/cast.json").read_text()).items()})
CAST.update({name.lower(): f"{name}: its reference image shows the ship's design only. Never "
                           f"paste or copy that picture into the scene: draw the ship fresh from this scene's camera angle, "
                           f"with its own lighting and in the same style as everything else. {ship['look']}"
             for name, ship in SHIPS.items()})
PRIORITY = ("THE MOST IMPORTANT THING IN THIS IMAGE: every fictional character who appears in the scene must be instantly "
            "recognisable as the character in their attached character art: the same face, hair, skin, build, outfit "
            "and props. All attached portraits are invented fantasy character art from a tabletop game, not real people. "
            "The characters' likeness comes before the setting, the style, the composition and every other instruction below.")
REFERENCES = ("Reference portraits attached, in order: {}. Each character in the scene must look "
              "as close to their portrait as possible: the same face and features, hair, skin, colours, build, "
              "proportions, outfit and props, so anyone who knows the portrait recognises them at once. This likeness is "
              "the most important thing in the image. Where a portrait and a text description disagree, the portrait "
              "wins. Each named ship keeps the design of its reference image (hull shape, sails, wings, rotors, engines, "
              "colours and flames) but is drawn fresh from the scene's angle. No reference image may appear pasted, flat "
              "or cut out anywhere in the picture.")
MAP_NOTE = ("After the portraits come top-down Roll20 battle maps of this place, in order: {}. Use them only for the layout, "
            "buildings, streets, terrain and colours. Never draw the scene from overhead or as a map, and ignore any text on them.")
LINEUP = "Character lineup"


@dataclasses.dataclass
class Request:
    event_id: str
    prompt: str
    refs: list  # (name, file) in the order attached
    lineup: list  # names drawn on the character outline, left to right
    style: str


@dataclasses.dataclass
class Image:
    event_id: str
    jpeg: bytes
    meta: dict


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def env(name):
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip()
    sys.exit(f"{name} missing from .env")


def keep(path):
    """Moves an existing file into an old/ folder beside it, stamped with the time, so nothing is ever overwritten."""
    path = pathlib.Path(path)
    if path.exists():
        old = path.parent / "old"
        old.mkdir(exist_ok=True)
        path.rename(old / f"{path.stem}.{time.strftime('%Y%m%d-%H%M%S')}{path.suffix}")


def small(path):
    """A 768px JPEG copy of a reference image, cached in gen/regen/refcache/."""
    out = ROOT / "gen/regen/refcache" / (path.stem + ".jpg")
    if not out.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["sips", "-Z", "768", "-s", "format", "jpeg", "-s", "formatOptions", "85", str(path), "--out", str(out)],
                       check=True, capture_output=True)
    return out


def post(url, body, headers):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", **headers})
    try:
        return json.load(urllib.request.urlopen(req, timeout=240))
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode()[:600]}")


def house_style():
    return (ROOT / "gen/world/tone.txt").read_text().split("Style:", 1)[1].split("\n", 1)[0].strip()


def setting(ref, session):
    """The setting block for "<setting-id>[/<sublocation-id>]" from gen/world/settings.json, as it looks at that session."""
    sid, _, sub = ref.strip().partition("/")
    s = next(x for x in json.loads((ROOT / "gen/world/settings.json").read_text()) if x["id"] == sid)
    lines = [f"{s['name']}: {s['look']}"]
    # only stages from earlier sessions; the prompt's own "In this moment" covers what happens this session
    periods = sorted((p for p in s.get("periods", []) if p["from_session"] < session), key=lambda p: p["from_session"])
    if periods:
        lines.append(f"Earlier in the story, this place saw: {periods[-1]['look_change']} Draw only lasting traces of "
                     f"that which would still be visible now; the moment below decides what is actually there.")
    if sub:
        loc = next(x for x in s["sublocations"] if x["id"] == sub)
        lines.append(f"{loc['name']}: {loc['look']}")
    return "\n".join(lines)


def maps_attached(prompt):
    """(label, file) for each Roll20 page in a {maps:Page|Page#2} placeholder; #n picks the page's nth image, default 1."""
    m = re.search(r"\{maps:([^}]+)\}", prompt)
    if not m:
        return []
    index = {p["page"].strip(): p for p in json.loads((ROOT / "gen/refs/roll20/maps/index.json").read_text())}
    out = []
    for item in m.group(1).split("|"):
        name, _, n = item.strip().partition("#")
        out.append((f"{name} map", ROOT / "gen/refs/roll20/maps" / index[name]["maps"][int(n or 1) - 1]["file"]))
    return out


def label(name, req):
    """The text placed right before each attached image, so the model knows whose it is."""
    if name == LINEUP:
        order = ", ".join(f"{i}. {n}" for i, n in enumerate(req.lineup, 1))
        return (f"Here is a lineup of the characters to reference, left to right, to scale: {order}. "
                f"Each appears once, with the skin and hair shown here, and the outfit shown here unless the scene "
                f"says they wear something else or nothing.")
    if name.endswith(" map"):
        return f"Next reference, {name}: layout reference only, not a view to copy."
    if name in SHIPS:
        return f"Next reference, {name}: this is what the ship {name} looks like."
    return (f"Next reference, {name}: fictional character art. If {name} is in the scene, the character must be instantly "
            f"recognisable from it: the same face, hair, build, colouring and outfit.")


def closing(req):
    """The text sent after all the images."""
    return (f"FINAL INSTRUCTION: above all, every character in the scene must be recognisable as their portrait. "
            f"Render the whole image, every character included, in one consistent style: {req.style}")


def build(event_id, style=None, lineup=True, prompt_file=None):
    """The prompt and attached references for an event, from gen/prompts/<event-id>.prompt.txt."""
    style = style or house_style()
    text = pathlib.Path(prompt_file or ROOT / "gen/prompts" / f"{event_id}.prompt.txt").read_text()
    if "{framing:epic}" in text:
        # an epic shot is a high, far view; the style's in-the-action camera would contradict it
        style = re.sub(r"A dynamic, tilted camera[^.]*\.\s*", "", style)
    ev = next(e for e in json.loads((ROOT / "site/timeline.json").read_text())["events"] if e["id"] == event_id)
    src = next((s for s in json.loads((ROOT / "gen/regen/sources.json").read_text()) if s["id"] == event_id), {"refs": []})
    cast_block = text.split("\nCAST", 1)[-1].split("\nREFERENCES", 1)[0]
    # the event's portraits plus every character the prompt's CAST names, as {cast:Name} or "- Name: ..."
    refs = {r["name"]: ROOT / r["file"] for r in src["refs"]}
    named = re.findall(r"\{cast:([^}]+)\}", cast_block) + re.findall(r"^- ([^:{\n]+): ", cast_block, flags=re.M)
    for n in dict.fromkeys(n.strip() for n in named):
        if n not in refs and (PORTRAITS.get(n) or {}).get("file"):
            refs[n] = ROOT / PORTRAITS[n]["file"]
    refs = {n: small(f) for n, f in refs.items()}
    in_sheet = []
    if lineup:
        sys.path.insert(0, str(ROOT / "gen"))
        from lineup import build as build_lineup, slug
        # only characters drawn in this moment ({cast:Name}), never the "reference only" ones
        in_moment = {n.strip() for n in re.findall(r"\{cast:([^}]+)\}", cast_block)}
        # someone transformed in this moment would be drawn in their usual form from the outline
        changed = {n.strip() for n in re.findall(
            r"\{cast:([^}]+)\}\s+Here:[^\n]*\b(?:transformed|wild-shaped|shapechanged|in [a-z]+ form)\b", cast_block)}
        in_sheet = [n for n in refs if n in in_moment - changed and (ROOT / "gen/refs/fullbody" / f"{slug(n)}.jpg").exists()]
        refs = {n: f for n, f in refs.items() if (n in in_moment and n not in changed) or n in SHIPS}
        if in_sheet:
            sheet = ROOT / "gen/regen/refcache" / f"lineup-{event_id}.jpg"
            build_lineup(sheet, in_sheet, labels=False)
            refs = {LINEUP: sheet} | {n: f for n, f in refs.items() if n not in in_sheet}
    tone = re.sub(r"^Style:.*$", lambda m: f"Style: {style}", (ROOT / "gen/world/tone.txt").read_text().strip(), flags=re.M)
    references = REFERENCES.format(", ".join(refs)) if refs else ""
    prompt = PRIORITY + "\n\n" + text.replace("{references}", references).replace("{tone}", tone)
    prompt = re.sub(r"\{setting:([^}]+)\}", lambda m: setting(m.group(1), ev.get("session") or 0), prompt)
    # "{cast:Name} Here: ..." is what's different in this moment, so it overrides the usual look described before it
    prompt = re.sub(r"(\{cast:[^}]+\})\s+Here:\s*", r"\1 IN THIS MOMENT, overriding the usual look above wherever they differ: ",
                    prompt)
    prompt = re.sub(r"\{cast:([^}]+)\}",
                    lambda m: CAST.get(m.group(1).strip().lower(), f"{m.group(1).strip()}: MISSING FROM CAST.JSON"), prompt)
    framing = json.loads((ROOT / "gen/world/framing.json").read_text())
    prompt = re.sub(r"\{framing:(\w+)\}", lambda m: framing[m.group(1)], prompt)
    maps = maps_attached(prompt)
    prompt = re.sub(r"\{maps:([^}]+)\}", lambda m: MAP_NOTE.format(", ".join(n for n, _ in maps)), prompt)
    refs |= {n: small(f) for n, f in maps}
    if in_sheet:
        prompt = prompt.replace("draw from the reference portrait.", "draw from their figure in the character lineup.")
    return Request(event_id, prompt, list(refs.items()), in_sheet, style)


def full_text(req):
    """Everything sent as text, in order: the prompt, each reference's label, the final instruction."""
    return "\n".join([req.prompt] + [label(n, req) for n, _ in req.refs] + [closing(req)])


def generate(event_id, style=None, lineup=True, model=MODEL, prompt_file=None):
    """Generates one image for the event and returns it; saves nothing."""
    req = build(event_id, style, lineup, prompt_file)
    if "MISSING FROM CAST.JSON" in req.prompt:
        sys.exit("prompt names a character missing from gen/world/cast.json")
    content = [{"type": "text", "text": req.prompt}]
    for name, path in req.refs:
        mime = "image/jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
        content += [{"type": "text", "text": label(name, req)},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"}}]
    content.append({"type": "text", "text": closing(req)})
    resp = post("https://openrouter.ai/api/v1/chat/completions",
                # a low max_tokens keeps OpenRouter's up-front credit hold small (an image is ~1,120 tokens)
                {"model": model, "messages": [{"role": "user", "content": content}], "modalities": ["image", "text"],
                 "image_config": {"aspect_ratio": "16:9"}, "max_tokens": 4000},
                {"Authorization": "Bearer " + env("OPENROUTER_API_KEY")})
    imgs = (resp.get("choices") or [{}])[0].get("message", {}).get("images") or []
    if not imgs:
        sys.exit("no image returned: " + json.dumps(resp)[:600])
    with tempfile.TemporaryDirectory() as tmp:
        raw, jpg = pathlib.Path(tmp, "raw"), pathlib.Path(tmp, "out.jpg")
        raw.write_bytes(base64.b64decode(imgs[0]["image_url"]["url"].split(",", 1)[1]))
        subprocess.run(["sips", "--resampleWidth", "1280", "-s", "format", "jpeg", "-s", "formatOptions", "80",
                        str(raw), "--out", str(jpg)], check=True, capture_output=True)
        jpeg = jpg.read_bytes()
    meta = {"model": model, "prompt": str(prompt_file or f"gen/prompts/{event_id}.prompt.txt"), "style": req.style,
            "lineup": req.lineup, "refs": [n for n, _ in req.refs], "cost": resp.get("usage", {}).get("cost"),
            "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    return Image(event_id, jpeg, meta)


def save_draft(image):
    """Saves an image under gen/drafts/<event-id>/ with its details beside it; never touches the site."""
    folder = ROOT / "gen/drafts" / image.event_id
    folder.mkdir(parents=True, exist_ok=True)
    out = folder / f"{time.strftime('%Y%m%d-%H%M%S')}-{time.time_ns() % 1_000_000:06d}.jpg"
    out.write_bytes(image.jpeg)
    out.with_suffix(".json").write_text(json.dumps(image.meta, indent=1) + "\n")
    return out


def save_version(image):
    """Saves an image as the event's next version, points the site at it and logs it; safe to run in parallel."""
    with open(ROOT / "site/timeline.json", "r+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        data = json.load(f)
        ev = next(e for e in data["events"] if e["id"] == image.event_id)
        version = ev.get("img_version", 1) + 1
        out = ROOT / f"site/img/{image.event_id}.v{version}.jpg"
        keep(out)
        out.write_bytes(image.jpeg)
        old = ev.get("img", "")
        if old.startswith("img/") and (ROOT / "site" / old).exists():
            dest = ROOT / "gen/test/old" / pathlib.Path(old).name
            dest.parent.mkdir(parents=True, exist_ok=True)
            keep(dest)
            (ROOT / "site" / old).rename(dest)
        ev["img"], ev["img_version"] = f"img/{out.name}", version
        f.seek(0)
        f.write(json.dumps(data, indent=2))
        f.truncate()
        log_path = ROOT / "gen/regen/versions.json"
        log = json.loads(log_path.read_text()) if log_path.exists() else {}
        log.setdefault(image.event_id, []).append({"version": version, "file": f"site/img/{out.name}"} | image.meta)
        log_path.write_text(json.dumps(log, indent=1) + "\n")
    return out


def load_draft(path):
    """A saved draft, read back as an Image so it can be saved as a version."""
    path = pathlib.Path(path)
    return Image(path.parent.name, path.read_bytes(), json.loads(path.with_suffix(".json").read_text()) | {"draft": str(path)})


def promote(path):
    """Makes a saved draft the event's next version on the site."""
    return save_version(load_draft(path))


def generate_scene(event_id, style=None, lineup=True, model=MODEL):
    """The canonical scene image: generate it, then save it as the event's next version."""
    return save_version(generate(event_id, style, lineup, model))


def main():
    event_id = sys.argv[1]
    style, lineup, model = arg("--style"), "--no-lineup" not in sys.argv, arg("--model", MODEL)
    if "--print" in sys.argv:
        print(full_text(build(event_id, style, lineup)))
        return
    image = generate(event_id, style, lineup, model)
    out = save_draft(image) if "--draft" in sys.argv else save_version(image)
    print(f"{event_id} ok -> {out.relative_to(ROOT)} refs={image.meta['refs']} model={model} cost={image.meta['cost']}")


if __name__ == "__main__":
    main()
