# The 100 Years War timeline

Interactive, zoomable timeline of the Eberron D&D campaign.

- `site/` is the whole app: `index.html`, `timeline.json` (calendar, eras, events), `img/` (generated scenes), `media/` (art from the campaign doc), and `edit_timeline/` (in-browser editor).
- Every push to `main` publishes `site/` to GitHub Pages via `.github/workflows/pages.yml`.
- `gen/prompts.json` + `gen/generate.py` regenerate images through OpenRouter. Put the key in `gen/key.txt` (gitignored). The script skips images that already exist.

Local preview: `python3 -m http.server 8788 --directory site` then open http://127.0.0.1:8788/.
