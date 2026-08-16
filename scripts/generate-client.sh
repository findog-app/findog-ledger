#! /usr/bin/env bash

set -e
set -x

openapi_tmp=$(mktemp)
trap 'rm -f "$openapi_tmp"' EXIT

(
  cd backend
  uv run python -c "import app.main; import json; print(json.dumps(app.main.app.openapi()))" > "$openapi_tmp"
)

OPENAPI_INPUT="$openapi_tmp" bash ./scripts/bun.sh run --filter frontend generate-client
bash ./scripts/bun.sh run --filter frontend lint
