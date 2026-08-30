"""Execute the scheduled System Run once and return a shell-friendly status."""

from __future__ import annotations

import logging

from app.core.db import SessionLocal
from app.services.system_run_runner import exit_code, run_scheduled_system_run


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    with SessionLocal() as session:
        return exit_code(run_scheduled_system_run(session=session))


if __name__ == "__main__":
    raise SystemExit(main())
