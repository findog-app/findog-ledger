#! /usr/bin/env bash

set -e
set -x

cd backend
uv run python -c "import app.main; import json; print(json.dumps(app.main.app.openapi()))" > ../openapi.json
cd ..
mv openapi.json frontend/
bash ./scripts/bun.sh run --filter frontend generate-client
bash ./scripts/bun.sh run --filter frontend lint
