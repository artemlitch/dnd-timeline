#!/usr/bin/env bash
set -euo pipefail

SITE_DIR="${1:-/private/tmp/claude-501/-Users-artemlitch-readwise-rekindled/6063c040-5e4e-4dec-8911-a6971a97ab2e/scratchpad/site}"
PROJECT="dnd-100-years-war"

OUT="$(npx --yes wrangler@latest pages deploy "$SITE_DIR" --project-name "$PROJECT" --branch main --commit-dirty=true 2>&1)"
printf '%s\n' "$OUT"
echo
echo "Deployed URL(s):"
printf '%s\n' "$OUT" | grep -oE 'https://[A-Za-z0-9.-]+\.pages\.dev' | sort -u
echo "Production: https://${PROJECT}.pages.dev"
