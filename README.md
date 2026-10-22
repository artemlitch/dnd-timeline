# The 100 Years War timeline

Interactive, zoomable timeline of the Eberron D&D campaign, built from the campaign doc.

- `site/` is the whole app: `index.html` (single file), `data.js` (events + eras), `img/` (generated scenes), `media/` (art from the campaign PDF).
- `gen/prompts.json` + `gen/generate.py` regenerate images through OpenRouter (`google/gemini-3.1-flash-lite-image`). Put the key in `gen/key.txt` (gitignored). The script skips images that already exist.
- `./deploy.sh` publishes `site/` to https://dnd-100-years-war.pages.dev.

Local preview: `python3 -m http.server 8787 --directory site` then open http://127.0.0.1:8787/.
