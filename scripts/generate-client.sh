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

# The generator may leave whitespace on otherwise empty lines. Normalize its
# output so a no-op regeneration does not make a commit hook fail.
find frontend/src/client -type f -name '*.ts' -exec perl -pi -e 's/[ \t]+$//' {} +

bash ./scripts/bun.sh run --filter frontend lint
