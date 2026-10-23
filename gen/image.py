"""Generate a timeline image for one event, attaching the PC reference portraits that appear in it.

usage: python3 -I gen/image.py <event-id> [--model openai/gpt-5-image-mini] [--provider openrouter|gemini] [--test]
  default: OpenRouter, google/gemini-3.1-flash-lite-image. Keys come from .env (OPENROUTER_API_KEY, GEMINI_API_KEY).
  --nojson writes the image but leaves timeline.json alone (for parallel batches).
  --sources attaches every portrait listed for the event in gen/regen/sources.json (NPCs from Roll20 included),
  shrunk to 768px, instead of only the PC portraits found in the event text.
  --test writes gen/test/<event-id>.<model>.jpg and leaves site/ untouched; otherwise writes site/img/<event-id>.jpg
  and sets the event's img in site/timeline.json.
"""
import base64, json, pathlib, subprocess, sys, tempfile, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
STYLE = ("Painterly dark-fantasy illustration in the style of Eberron pulp-noir cover art, magic-steampunk: brass, "
         "elemental fire rings, glowing arcane runes, lightning rails, airships. Cinematic lighting, wide 16:9 "
         "composition, no text, no lettering, no watermark.")
CAST = {
    "lirael": "Lirael: a 23-year-old male drow sorcerer, slender, dark grey-blue skin, white hair, black Sentinel coat.",
    "brand": "Brand: a 150-year-old male dwarf artificer, spry and stocky, bearded, in a brass-and-steel power armor suit with a glowing holy core.",
    "sazed": "Sazed: a man of about 45 with elven features and more body and facial hair than usual (a shifter, but fully humanoid, not a beast or werewolf), lean monk build, quarterstaff, black covert ops suit.",
}


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
    mime = {n: "image/jpeg" if files[n].suffix.lower() in (".jpg", ".jpeg") else "image/png" for n in refs}
    b64 = {n: base64.b64encode(files[n].read_bytes()).decode() for n in refs}

    if provider == "gemini":
        parts = [{"text": prompt}] + [{"inline_data": {"mime_type": mime[n], "data": b64[n]}} for n in refs]
        resp = post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                    {"contents": [{"parts": parts}], "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "16:9"}}},
                    {"x-goog-api-key": env("GEMINI_API_KEY")})
        img = next((p["inlineData"]["data"] for c in resp.get("candidates", []) for p in c["content"]["parts"] if "inlineData" in p), None)
        cost = None
    else:
        content = [{"type": "text", "text": prompt}] + [{"type": "image_url", "image_url": {"url": f"data:{mime[n]};base64,{b64[n]}"}} for n in refs]
        resp = post("https://openrouter.ai/api/v1/chat/completions",
                    {"model": model, "messages": [{"role": "user", "content": content}], "modalities": ["image", "text"], "image_config": {"aspect_ratio": "16:9"}},
                    {"Authorization": "Bearer " + env("OPENROUTER_API_KEY")})
        imgs = (resp.get("choices") or [{}])[0].get("message", {}).get("images") or []
        img = imgs[0]["image_url"]["url"].split(",", 1)[1] if imgs else None
        cost = resp.get("usage", {}).get("cost")
    if not img:
        sys.exit("no image returned: " + json.dumps(resp)[:600])

    out = ROOT / (f"gen/test/{event_id}.{model.split('/')[-1]}.jpg" if test else f"site/img/{event_id}.jpg")
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".img") as tmp:
        tmp.write(base64.b64decode(img))
        tmp.flush()
        subprocess.run(["sips", "--resampleWidth", "1280", "-s", "format", "jpeg", "-s", "formatOptions", "80",
                        tmp.name, "--out", str(out)], check=True, capture_output=True)
    if not test and "--nojson" not in sys.argv:
        ev["img"] = f"img/{event_id}.jpg"
        (ROOT / "site/timeline.json").write_text(json.dumps(data, indent=2))
    print(f"{event_id} ok -> {out.relative_to(ROOT)} ({out.stat().st_size} bytes) refs={refs} model={model} cost={cost}")


if __name__ == "__main__":
    main()
