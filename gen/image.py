"""Generate a timeline image for one event, attaching the PC reference portraits that appear in it.

usage: python3 -I gen/image.py <event-id> [--model openai/gpt-5-image-mini] [--provider openrouter|gemini] [--test]
  default: OpenRouter, google/gemini-3.1-flash-lite-image. Keys come from .env (OPENROUTER_API_KEY, GEMINI_API_KEY).
  --nojson writes the image but leaves timeline.json alone (for parallel batches).
  --sources attaches every portrait listed for the event in gen/regen/sources.json (NPCs from Roll20 included),
  shrunk to 768px, instead of only the PC portraits found in the event text.
  --size <0.5K|1K|2K> asks OpenRouter for that output size.
  --prompt <file> sends that file as the whole prompt, with {references} replaced by the portrait-likeness line and
  {tone} by gen/world/tone.txt and {setting:<id>[/<sublocation-id>]} by that entry of gen/world/settings.json as it
  looks at the event's session, {cast:Name} by that character's line in gen/world/cast.json, {framing:<epic|wide|medium|close>} by gen/world/framing.json, and {maps:Page|Page}
  attaches those Roll20 pages' maps after the portraits. --print shows the finished prompt without generating anything.
  --test writes gen/test/<event-id>.<model>.jpg and leaves site/ untouched; otherwise writes site/img/<event-id>.jpg
  and sets the event's img in site/timeline.json.
"""
import base64, json, pathlib, re, subprocess, sys, tempfile, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
STYLE = ("Painterly dark-fantasy illustration in the style of Eberron pulp-noir cover art, magic-steampunk: brass, "
         "elemental fire rings, glowing arcane runes, lightning rails, airships. Cinematic lighting, wide 16:9 "
         "composition, no text, no lettering, no watermark.")
CAST = {name.lower(): f"{name}: {text}" for name, text in json.loads((ROOT / "gen/world/cast.json").read_text()).items()}


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def env(name):
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip()
    sys.exit(f"{name} missing from .env")


def small(path):
    """A 768px JPEG copy of a reference image, cached in gen/regen/refcache/."""
    out = ROOT / "gen/regen/refcache" / (path.stem + ".jpg")
    if not out.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["sips", "-Z", "768", "-s", "format", "jpeg", "-s", "formatOptions", "85", str(path), "--out", str(out)],
                       check=True, capture_output=True)
    return out


def setting(ref, session):
    """The setting block for "<setting-id>[/<sublocation-id>]" from gen/world/settings.json, as it looks at that session."""
    sid, _, sub = ref.strip().partition("/")
    s = next(x for x in json.loads((ROOT / "gen/world/settings.json").read_text()) if x["id"] == sid)
    lines = [f"{s['name']}: {s['look']}"]
    periods = sorted((p for p in s.get("periods", []) if p["from_session"] <= session), key=lambda p: p["from_session"])
    if periods:
        lines.append(f"At this point in the story: {periods[-1]['look_change']}")
    if sub:
        loc = next(x for x in s["sublocations"] if x["id"] == sub)
        lines.append(f"{loc['name']}: {loc['look']}")
    return "\n".join(lines)


REFERENCES = ("Reference portraits attached, in order: {}. These portraits are NOT in this image's style: they are drawings, "
              "paintings and cartoons in many different styles. Use them only to know what each character looks like, then "
              "render that character in the style described above. Within that style, each named character must look as "
              "close to their portrait as possible: the same face and features, hair, skin, colours, build, proportions, "
              "outfit and props, so anyone who knows the portrait recognises them at once.")
MAP_NOTE = ("After the portraits come top-down Roll20 battle maps of this place, in order: {}. Use them only for the layout, "
            "buildings, streets, terrain and colours. Never draw the scene from overhead or as a map, and ignore any text on them.")


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


def post(url, body, headers):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", **headers})
    try:
        return json.load(urllib.request.urlopen(req, timeout=240))
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode()[:600]}")


def main():
    event_id, test = sys.argv[1], "--test" in sys.argv
    provider = arg("--provider", "openrouter")
    model = arg("--model", "google/gemini-3.1-flash-lite-image" if provider == "openrouter" else "gemini-3.1-flash-lite-image")
    data = json.loads((ROOT / "site/timeline.json").read_text())
    ev = next(e for e in data["events"] if e["id"] == event_id)
    text = " ".join([ev["title"], ev["summary"], ev["detail"], " ".join(ev.get("tags", []))]).lower()
    cast = [n for n in CAST if n in text]
    if "--sources" in sys.argv:
        src = next(s for s in json.loads((ROOT / "gen/regen/sources.json").read_text()) if s["id"] == event_id)
        refs = [r["name"] for r in src["refs"]]
        files = {r["name"]: small(ROOT / r["file"]) for r in src["refs"]}
    else:
        refs = [n.title() for n in cast if (ROOT / f"gen/refs/{n}.png").exists()]
        files = {n: ROOT / f"gen/refs/{n.lower()}.png" for n in refs}
    prompt = (f"{STYLE}\nScene: {ev['title']}. {ev['summary']} {ev['detail']}\n"
              + ("Characters: " + " ".join(CAST[n] for n in cast) + "\n" if cast else "")
              + (f"Reference portraits attached, in order: {', '.join(refs)}. "
                 "Match each character's face, build, hair and outfit to their portrait." if refs else ""))
    if "--prompt" in sys.argv:
        prompt = ((ROOT / arg("--prompt")).read_text().replace("{references}", REFERENCES.format(", ".join(refs)))
                  .replace("{tone}", (ROOT / "gen/world/tone.txt").read_text().strip()))
        prompt = re.sub(r"\{setting:([^}]+)\}", lambda m: setting(m.group(1), ev.get("session") or 0), prompt)
        prompt = re.sub(r"\{cast:([^}]+)\}", lambda m: CAST[m.group(1).strip().lower()], prompt)
        framing = json.loads((ROOT / "gen/world/framing.json").read_text())
        prompt = re.sub(r"\{framing:(\w+)\}", lambda m: framing[m.group(1)], prompt)
        maps = maps_attached(prompt)
        prompt = re.sub(r"\{maps:([^}]+)\}", lambda m: MAP_NOTE.format(", ".join(n for n, _ in maps)), prompt)
        for label, path in maps:
            refs.append(label)
            files[label] = small(path)
    if "--print" in sys.argv:
        print(prompt)
        return
    mime = {n: "image/jpeg" if files[n].suffix.lower() in (".jpg", ".jpeg") else "image/png" for n in refs}
    b64 = {n: base64.b64encode(files[n].read_bytes()).decode() for n in refs}

    if provider == "gemini":
        parts = [{"text": prompt}] + [{"inline_data": {"mime_type": mime[n], "data": b64[n]}} for n in refs]
        resp = post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                    {"contents": [{"parts": parts}], "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {
                        "aspectRatio": "16:9", **({"imageSize": arg("--size")} if "--size" in sys.argv else {})}}},
                    {"x-goog-api-key": env("GEMINI_API_KEY")})
        print("usage", json.dumps(resp.get("usageMetadata", {})))
        img = next((p["inlineData"]["data"] for c in resp.get("candidates", []) for p in c["content"]["parts"] if "inlineData" in p), None)
        cost = None
    else:
        content = [{"type": "text", "text": prompt}] + [{"type": "image_url", "image_url": {"url": f"data:{mime[n]};base64,{b64[n]}"}} for n in refs]
        image_config = {"aspect_ratio": "16:9", **({"image_size": arg("--size")} if "--size" in sys.argv else {})}
        resp = post("https://openrouter.ai/api/v1/chat/completions",
                    {"model": model, "messages": [{"role": "user", "content": content}], "modalities": ["image", "text"], "image_config": image_config,
                     **({"provider": {"order": [arg("--route")], "allow_fallbacks": False}} if "--route" in sys.argv else {})},
                    {"Authorization": "Bearer " + env("OPENROUTER_API_KEY")})
        print("usage", json.dumps(resp.get("usage", {})))
        imgs = (resp.get("choices") or [{}])[0].get("message", {}).get("images") or []
        img = imgs[0]["image_url"]["url"].split(",", 1)[1] if imgs else None
        cost = resp.get("usage", {}).get("cost")
    if not img:
        sys.exit("no image returned: " + json.dumps(resp)[:600])

    size = f".{arg('--size')}" if "--size" in sys.argv else ""
    out = ROOT / (f"gen/test/{event_id}.{model.split('/')[-1]}{size}.jpg" if test else f"site/img/{event_id}.jpg")
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".img") as tmp:
        tmp.write(base64.b64decode(img))
        tmp.flush()
        dims = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", tmp.name], capture_output=True, text=True).stdout.split()
        print("generated", dims[-3], "x", dims[-1])
        subprocess.run(["sips", "--resampleWidth", "1280", "-s", "format", "jpeg", "-s", "formatOptions", "80",
                        tmp.name, "--out", str(out)], check=True, capture_output=True)
    if not test and "--nojson" not in sys.argv:
        ev["img"] = f"img/{event_id}.jpg"
        (ROOT / "site/timeline.json").write_text(json.dumps(data, indent=2))
    print(f"{event_id} ok -> {out.relative_to(ROOT)} ({out.stat().st_size} bytes) refs={refs} model={model} cost={cost}")


if __name__ == "__main__":
    main()
