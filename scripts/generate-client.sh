#! /usr/bin/env bash

set -e
set -x

cd backend
uv run python -c "import app.main; import json; print(json.dumps(app.main.app.openapi()))" > ../openapi.json
cd ..
mv openapi.json frontend/
if command -v bun >/dev/null 2>&1; then
    bun run --filter frontend generate-client
    bun run lint
else
    npm --workspace frontend run generate-client
    npm run lint --workspace frontend
fi
