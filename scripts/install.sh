#!/usr/bin/env bash
set -euo pipefail

BASE_URL="https://raw.githubusercontent.com/oblidog/oblidog-ledger/main"

curl -fsSL "$BASE_URL/compose.production.yml" -o compose.yml

if [ ! -f .env ]; then
  curl -fsSL "$BASE_URL/.env.production.example" -o .env
  echo "Created .env from production template."
else
  echo ".env already exists; leaving it unchanged."
fi

echo
printf '%s\n' \
  "Oblidog Ledger deployment files are ready." \
  "" \
  "Next steps:" \
  "  1. Edit .env" \
  "  2. docker compose pull" \
  "  3. docker compose up -d"
