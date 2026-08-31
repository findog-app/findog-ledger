"""Process-safe runner for scheduled system work."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import cast
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, update
from sqlalchemy.engine import Connection, CursorResult
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain.system_run import SystemRunStatus, SystemRunTrigger
from app.models import SystemRun, SystemRunStep
from app.use_cases.system_runs import SystemRunContext, SystemRunOrchestrator

logger = logging.getLogger(__name__)

# This stable, application-specific key is shared by every deployment replica.
SYSTEM_RUN_ADVISORY_LOCK_KEY = 149_000_001


def run_scheduled_system_run(
    *,
    session: Session,
    effective_at: datetime | None = None,
    timezone: ZoneInfo | None = None,
    orchestrator: SystemRunOrchestrator | None = None,
) -> SystemRun | None:
    """Run once when the database advisory lock is available.

    PostgreSQL releases session advisory locks when a process crashes or loses its
    connection, so a crashed scheduler cannot leave a permanent lock behind.
    """
    now = effective_at or datetime.now(UTC)
    execution_timezone = timezone or ZoneInfo(settings.SYSTEM_RUN_TIMEZONE)
    return run_system_run(
        session=session,
        context=SystemRunContext.create(
            effective_at=now,
            timezone=execution_timezone,
            trigger=SystemRunTrigger.SCHEDULED,
        ),
        orchestrator=orchestrator,
    )


def run_system_run(
    *,
    session: Session,
    context: SystemRunContext,
    task_names: Iterable[str] | None = None,
    orchestrator: SystemRunOrchestrator | None = None,
) -> SystemRun | None:
    """Run one shared orchestrator execution while holding the database lock."""
    requested_tasks = tuple(task_names) if task_names is not None else None
    bind = session.get_bind()
    if isinstance(bind, Connection):
        return _run_with_lock(
            session=session,
            context=context,
            task_names=requested_tasks,
            orchestrator=orchestrator,
        )

    # Keep a dedicated database connection for the whole run. The shared
    # orchestrator commits after every persisted step, and a pooled Session may
    # otherwise return its connection (and session advisory lock) between steps.
    with bind.connect() as connection:
        with Session(bind=connection, expire_on_commit=False) as locked_session:
            return _run_with_lock(
                session=locked_session,
                context=context,
                task_names=requested_tasks,
                orchestrator=orchestrator,
            )


def _run_with_lock(
    *,
    session: Session,
    context: SystemRunContext,
    task_names: tuple[str, ...] | None,
    orchestrator: SystemRunOrchestrator | None,
) -> SystemRun | None:
    acquired = session.scalar(
        select(func.pg_try_advisory_lock(SYSTEM_RUN_ADVISORY_LOCK_KEY))
    )
    if not acquired:
        logger.info("system-run skipped because another scheduled run owns the lock")
        return None

    try:
        recover_stale_system_runs(session=session, now=context.effective_at)
        run = (orchestrator or SystemRunOrchestrator()).run(
            session=session, context=context, task_names=task_names
        )
        _log_run(run=run, session=session)
        return run
    finally:
        session.execute(select(func.pg_advisory_unlock(SYSTEM_RUN_ADVISORY_LOCK_KEY)))
        session.commit()


def recover_stale_system_runs(*, session: Session, now: datetime) -> int:
    """Finish abandoned run records before starting a fresh scheduled run."""
    cutoff = now - timedelta(minutes=settings.SYSTEM_RUN_STALE_AFTER_MINUTES)
    result = cast(
        CursorResult[object],
        session.execute(
            update(SystemRun)
            .where(
                SystemRun.status == SystemRunStatus.RUNNING,
                SystemRun.started_at < cutoff,
            )
            .values(
                status=SystemRunStatus.FAILURE,
                error="System run exceeded the stale-run timeout",
                finished_at=now,
            )
        ),
    )
    session.commit()
    recovered = result.rowcount or 0
    if recovered:
        logger.warning("recovered %s stale system run(s)", recovered)
    return recovered


def exit_code(run: SystemRun | None) -> int:
    """Map a completed run to the one-shot process contract."""
    if run is None:
        return 2
    return 0 if run.status is SystemRunStatus.SUCCESS else 1


def _log_run(*, run: SystemRun, session: Session) -> None:
    logger.info("system-run finished run_id=%s status=%s", run.id, run.status)
    for step in session.scalars(
        select(SystemRunStep).where(SystemRunStep.system_run_id == run.id)
    ):
        logger.info(
            "system-run step run_id=%s step_id=%s task=%s status=%s ledger_id=%s",
            run.id,
            step.id,
            step.task_name,
            step.status,
            step.ledger_id,
        )
