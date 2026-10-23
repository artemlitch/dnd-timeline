"""Checks every gen/prompts/*.prompt.txt: unknown {cast:} names, hand-written cast lines for characters cast.json
already describes, and placeholders left unfilled. --fix swaps those hand-written lines for {cast:Name}.

    python3 -I gen/prompts/check.py [--fix]
"""
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
cast = json.loads((ROOT / "gen/world/cast.json").read_text())
missing, inline, broken = {}, {}, []
for p in sorted((ROOT / "gen/prompts").glob("*.prompt.txt")):
    text = p.read_text()
    for name in re.findall(r"\{cast:([^}]+)\}", text):
        if name.strip() not in cast:
            missing.setdefault(name.strip(), []).append(p.stem.split(".")[0])
    cast_block = text.split("CAST", 1)[-1].split("REFERENCES", 1)[0]
    for name in re.findall(r"^- ([^:{\n]+): ", cast_block, flags=re.M):
        if name.strip() in cast:
            inline.setdefault(p.name, []).append(name.strip())
    if "--fix" in sys.argv and p.name in inline:
        new = text
        for name in inline[p.name]:
            new = re.sub(rf"^- {re.escape(name)}: .*$", f"- {{cast:{name}}}", new, count=1, flags=re.M)
        p.write_text(new)
    eid = p.name.removesuffix(".prompt.txt")
    r = subprocess.run([sys.executable, "-I", str(ROOT / "gen/image.py"), eid, "--print"], capture_output=True, text=True)
    if r.returncode or re.search(r"\{(tone|setting|cast|maps|framing|references)[:}]", r.stdout):
        broken.append(f"{eid}: {(r.stderr or r.stdout).strip()[-200:]}")

print("missing from cast.json:", json.dumps(missing, indent=1))
print("hand-written lines for cast.json characters:", sum(map(len, inline.values())), "in", len(inline), "files",
      "(fixed)" if "--fix" in sys.argv else "")
print("broken:", "\n".join(broken) or "none")
