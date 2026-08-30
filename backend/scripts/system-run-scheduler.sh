#!/bin/sh
set -eu

: "${SYSTEM_RUN_SCHEDULE:=5 0 * * *}"
: "${SYSTEM_RUN_TIMEZONE:=Europe/Warsaw}"

case "$SYSTEM_RUN_SCHEDULE" in
  *"
"* | *""*)
    echo "SYSTEM_RUN_SCHEDULE must be a single cron line" >&2
    exit 2
    ;;
esac

# cron starts jobs with a minimal environment. Preserve the service environment
# (including database configuration) in a root-only shell fragment instead of
# embedding credentials in the crontab command.
umask 077
python -c 'import os, shlex; print("\n".join(f"export {key}={shlex.quote(value)}" for key, value in os.environ.items() if key.isidentifier()))' \
  > /run/system-run.env

cat > /etc/cron.d/system-run <<EOF
SHELL=/bin/sh
PATH=/app/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
CRON_TZ=$SYSTEM_RUN_TIMEZONE
$SYSTEM_RUN_SCHEDULE root /app/backend/scripts/system-run-once.sh >> /proc/1/fd/1 2>&1
EOF
chmod 0644 /etc/cron.d/system-run

exec cron -f
