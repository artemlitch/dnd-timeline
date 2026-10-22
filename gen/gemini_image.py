"""Generate one timeline image with Gemini, attaching the PC reference portraits.

usage: python3 -I gen/gemini_image.py <event-id> [--model gemini-3.1-flash-lite-image]
Reads GEMINI_API_KEY from .env; writes site/img/<event-id>.jpg and sets the event's img in site/timeline.json.
"""
import base64, json, os, pathlib, subprocess, sys, tempfile, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
STYLE = ("Painterly dark-fantasy illustration in the style of Eberron pulp-noir cover art, magic-steampunk: brass, "
         "elemental fire rings, glowing arcane runes, lightning rails, airships. Cinematic lighting, wide 16:9 "
         "composition, no text, no lettering, no watermark.")
CAST = {
    "lirael": "Lirael: a 23-year-old male drow sorcerer, slender, dark grey-blue skin, white hair, black Sentinel coat.",
    "brand": "Brand: a 150-year-old male dwarf artificer, spry and stocky, bearded, in a brass-and-steel power armor suit with a glowing holy core.",
    "sazed": "Sazed: a man of about 45 with elven features and more body and facial hair than usual (a shifter, but fully humanoid, not a beast or werewolf), lean monk build, quarterstaff, black covert ops suit.",
}


def key():
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("GEMINI_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit("GEMINI_API_KEY missing from .env")


def main():
    event_id = sys.argv[1]
    model = sys.argv[sys.argv.index("--model") + 1] if "--model" in sys.argv else "gemini-3.1-flash-lite-image"
    data = json.loads((ROOT / "site/timeline.json").read_text())
    ev = next(e for e in data["events"] if e["id"] == event_id)
    text = " ".join([ev["title"], ev["summary"], ev["detail"], " ".join(ev.get("tags", []))]).lower()
    cast = [n for n in CAST if n in text]
    refs = [n for n in cast if (ROOT / f"gen/refs/{n}.png").exists()]

    prompt = (f"{STYLE}\nScene: {ev['title']}. {ev['summary']} {ev['detail']}\n"
              + ("Characters: " + " ".join(CAST[n] for n in cast) + "\n" if cast else "")
              + (f"Reference portraits attached, in order: {', '.join(n.title() for n in refs)}. "
                 "Match each character's face, build, hair and outfit to their portrait." if refs else ""))
    parts = [{"text": prompt}] + [
        {"inline_data": {"mime_type": "image/png", "data": base64.b64encode((ROOT / f"gen/refs/{n}.png").read_bytes()).decode()}}
        for n in refs]
    body = {"contents": [{"parts": parts}], "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "16:9"}}}
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(body).encode(), headers={"x-goog-api-key": key(), "Content-Type": "application/json"})
    resp = json.load(urllib.request.urlopen(req, timeout=180))
    img = next((p["inlineData"] for c in resp.get("candidates", []) for p in c["content"]["parts"] if "inlineData" in p), None)
    if not img:
        sys.exit("no image returned: " + json.dumps(resp)[:500])

    out = ROOT / f"site/img/{event_id}.jpg"
    with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
        tmp.write(base64.b64decode(img["data"]))
        tmp.flush()
        subprocess.run(["sips", "--resampleWidth", "1280", "-s", "format", "jpeg", "-s", "formatOptions", "80",
                        tmp.name, "--out", str(out)], check=True, capture_output=True)
    ev["img"] = f"img/{event_id}.jpg"
    (ROOT / "site/timeline.json").write_text(json.dumps(data, indent=2))
    usage = resp.get("usageMetadata", {})
    print(f"{event_id} ok {out.stat().st_size} bytes, refs={refs}, model={model}, tokens={usage.get('totalTokenCount')}")


if __name__ == "__main__":
    main()
