#!/usr/bin/env bash
set -euo pipefail

SITE_DIR="${1:-$(cd "$(dirname "$0")" && pwd)/site}"
PROJECT="dnd-100-years-war"

OUT="$(npx --yes wrangler@latest pages deploy "$SITE_DIR" --project-name "$PROJECT" --branch main --commit-dirty=true 2>&1)"
printf '%s\n' "$OUT"
echo
echo "Deployed URL(s):"
printf '%s\n' "$OUT" | grep -oE 'https://[A-Za-z0-9.-]+\.pages\.dev' | sort -u
echo "Production: https://${PROJECT}.pages.dev"
