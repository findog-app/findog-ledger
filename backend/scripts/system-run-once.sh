#!/bin/sh
set -eu

. /run/system-run.env
: "${SYSTEM_RUN_TIMEOUT_SECONDS:=3600}"

if timeout --signal=TERM --kill-after=30s "${SYSTEM_RUN_TIMEOUT_SECONDS}s" \
  /app/.venv/bin/python -m app.jobs.system_run; then
  exit 0
else
  exit_code=$?
fi

echo "System Run one-shot exited with status ${exit_code}" >&2
exit "$exit_code"
