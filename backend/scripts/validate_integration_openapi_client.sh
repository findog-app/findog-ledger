#!/usr/bin/env bash

set -euo pipefail

output_dir=$(mktemp -d)
trap 'rm -rf "$output_dir"' EXIT

openapi-python-client generate \
  --path ../openapi/integration.json \
  --output-path "$output_dir/client" \
  --overwrite \
  --fail-on-warning

client_dir="$output_dir/client/findog_integration_api_client"

test -f "$client_dir/models/category_data_record_public.py"
test -f "$client_dir/models/category_data_records_public.py"
test "$(grep -rl 'CategoryDataRecordPublic' "$client_dir/api" | wc -l)" -ge 2
test "$(grep -rl 'CategoryDataRecordsPublic' "$client_dir/api" | wc -l)" -ge 1
