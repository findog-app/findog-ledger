"""Application-level orchestration for repeatable system work.

This module deliberately has no HTTP or scheduler dependency.  A scheduler can
call ``SystemRunOrchestrator.run`` with its static registry, while a future
manual UI can explicitly select a manual-only task.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from typing import Protocol, cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain import BillingPeriod, TaskRunMode
from app.domain.system_run import (
    SystemRunSkipReason,
    SystemRunStatus,
    SystemRunStepStatus,
)
from app.models import Ledger, SystemRun, SystemRunStep
from app.services.legacy_import import load_legacy_import_config
from app.use_cases import legacy_import as legacy_import_use_cases
from app.use_cases import obligations as obligation_use_cases


class SystemRunTask(Protocol):
    """A task adapter around an existing application use case."""

    name: str
    mode: TaskRunMode
    dependencies: tuple[str, ...]

    def is_configured(self) -> bool: ...

    def is_due(self, run_at: datetime) -> bool: ...

    def run(self, *, session: Session, ledger: Ledger, run_at: datetime) -> None: ...


class EnsureObligationsTask:
    name = "ensure_obligations"
    mode = TaskRunMode.SCHEDULED
    dependencies: tuple[str, ...] = ()

    def is_configured(self) -> bool:
        return True

    def is_due(self, run_at: datetime) -> bool:
        return True

    def run(self, *, session: Session, ledger: Ledger, run_at: datetime) -> None:
        obligation_use_cases.ensure_obligations_for_period(
            session=session,
            ledger_id=ledger.id,
            period=BillingPeriod.from_date(run_at.date()),
        )


class LegacyImportTask:
    name = "legacy_import"
    dependencies: tuple[str, ...] = ()

    @property
    def mode(self) -> TaskRunMode:
        return settings.LEGACY_IMPORT_MODE

    def is_configured(self) -> bool:
        return bool(
            settings.DROPBOX_API_KEY and settings.LEGACY_IMPORT_CONFIG_PATH.is_file()
        )

    def is_due(self, run_at: datetime) -> bool:
        return True

    def run(self, *, session: Session, ledger: Ledger, run_at: datetime) -> None:
        # The import use case owns validation, replacement and transaction
        # handling; this adapter only obtains its external input.
        from findog_legacy_adapter import (  # type: ignore[import-untyped]
            load_payment_book_from_dropbox,
        )

        config = load_legacy_import_config(settings.LEGACY_IMPORT_CONFIG_PATH)
        payment_book = load_payment_book_from_dropbox(
            settings.DROPBOX_API_KEY,
            config.excel_dropbox_path,
            config.monitored_sheets,
            interpret_codes=True,
        )
        legacy_import_use_cases.import_legacy_payment_book(
            session=session,
            ledger_id=ledger.id,
            payment_book=payment_book,
            current_period=BillingPeriod.from_date(run_at.date()),
        )


SYSTEM_RUN_TASK_REGISTRY: tuple[SystemRunTask, ...] = (
    cast(SystemRunTask, EnsureObligationsTask()),
    cast(SystemRunTask, LegacyImportTask()),
)


class SystemRunOrchestrator:
    def __init__(
        self, tasks: Sequence[SystemRunTask] = SYSTEM_RUN_TASK_REGISTRY
    ) -> None:
        self.tasks = _ordered_tasks(tasks)

    def run(
        self,
        *,
        session: Session,
        run_at: datetime | None = None,
        task_names: Iterable[str] | None = None,
    ) -> SystemRun:
        """Run scheduled work, or explicitly selected manual-only work.

        With no ``task_names`` only scheduled tasks are selected.  Consequently
        manual-only work can never be started implicitly.
        """
        now = (run_at or datetime.now(UTC)).astimezone(UTC)
        requested = set(task_names) if task_names is not None else None
        if requested is not None:
            known = {task.name for task in self.tasks}
            unknown = requested - known
            if unknown:
                raise ValueError(
                    f"Unknown system-run tasks: {', '.join(sorted(unknown))}"
                )

        system_run = SystemRun(status=SystemRunStatus.RUNNING, started_at=now)
        session.add(system_run)
        session.commit()
        session.refresh(system_run)
        failed_targets: set[tuple[str, object]] = set()

        for task in self.tasks:
            if requested is not None and task.name not in requested:
                continue
            if requested is None and task.mode is not TaskRunMode.SCHEDULED:
                self._skip_task(
                    session, system_run, task.name, _mode_reason(task.mode), now
                )
                continue
            if task.mode is TaskRunMode.DISABLED:
                self._skip_task(
                    session, system_run, task.name, SystemRunSkipReason.DISABLED, now
                )
                continue
            if not task.is_configured():
                self._skip_task(
                    session,
                    system_run,
                    task.name,
                    SystemRunSkipReason.NOT_CONFIGURED,
                    now,
                )
                continue
            if not task.is_due(now):
                self._skip_task(
                    session, system_run, task.name, SystemRunSkipReason.NOT_DUE, now
                )
                continue

            ledgers = list(
                session.scalars(
                    select(Ledger).where(Ledger.is_active).order_by(Ledger.id)
                ).all()
            )
            if not ledgers:
                self._skip_task(
                    session,
                    system_run,
                    task.name,
                    SystemRunSkipReason.NO_ELIGIBLE_TARGETS,
                    now,
                )
                continue
            for ledger in ledgers:
                if any(
                    (dependency, ledger.id) in failed_targets
                    for dependency in task.dependencies
                ):
                    self._add_step(
                        session,
                        system_run,
                        task.name,
                        ledger.id,
                        SystemRunStepStatus.SKIPPED,
                        now,
                        skip_reason=SystemRunSkipReason.PREREQUISITE_FAILED,
                    )
                    continue
                try:
                    task.run(session=session, ledger=ledger, run_at=now)
                except Exception as exc:
                    session.rollback()
                    failed_targets.add((task.name, ledger.id))
                    self._add_step(
                        session,
                        system_run,
                        task.name,
                        ledger.id,
                        SystemRunStepStatus.FAILED,
                        now,
                        error=str(exc),
                    )
                else:
                    self._add_step(
                        session,
                        system_run,
                        task.name,
                        ledger.id,
                        SystemRunStepStatus.SUCCEEDED,
                        now,
                    )

        steps = list(
            session.scalars(
                select(SystemRunStep).where(
                    SystemRunStep.system_run_id == system_run.id
                )
            ).all()
        )
        failed = sum(step.status is SystemRunStepStatus.FAILED for step in steps)
        succeeded = sum(step.status is SystemRunStepStatus.SUCCEEDED for step in steps)
        system_run.status = (
            SystemRunStatus.PARTIAL_FAILURE
            if failed and succeeded
            else SystemRunStatus.FAILURE
            if failed
            else SystemRunStatus.SUCCESS
        )
        system_run.finished_at = datetime.now(UTC)
        session.commit()
        session.refresh(system_run)
        return system_run

    @staticmethod
    def _skip_task(
        session: Session,
        system_run: SystemRun,
        task_name: str,
        reason: SystemRunSkipReason,
        now: datetime,
    ) -> None:
        SystemRunOrchestrator._add_step(
            session,
            system_run,
            task_name,
            None,
            SystemRunStepStatus.SKIPPED,
            now,
            skip_reason=reason,
        )

    @staticmethod
    def _add_step(
        session: Session,
        system_run: SystemRun,
        task_name: str,
        ledger_id: object | None,
        status: SystemRunStepStatus,
        now: datetime,
        *,
        skip_reason: SystemRunSkipReason | None = None,
        error: str | None = None,
    ) -> None:
        session.add(
            SystemRunStep(
                system_run_id=system_run.id,
                task_name=task_name,
                ledger_id=ledger_id,
                status=status,
                skip_reason=skip_reason,
                error=error,
                started_at=now,
                finished_at=datetime.now(UTC),
            )
        )
        session.commit()


def _mode_reason(mode: TaskRunMode) -> SystemRunSkipReason:
    return (
        SystemRunSkipReason.DISABLED
        if mode is TaskRunMode.DISABLED
        else SystemRunSkipReason.MANUAL_ONLY
    )


def _ordered_tasks(tasks: Sequence[SystemRunTask]) -> tuple[SystemRunTask, ...]:
    by_name = {task.name: task for task in tasks}
    if len(by_name) != len(tasks):
        raise ValueError("System-run task names must be unique")
    ordered: list[SystemRunTask] = []
    resolved: set[str] = set()
    while len(ordered) < len(tasks):
        ready = [
            task
            for task in tasks
            if task.name not in resolved
            and all(dependency in resolved for dependency in task.dependencies)
        ]
        if not ready:
            unknown = {
                dependency
                for task in tasks
                for dependency in task.dependencies
                if dependency not in by_name
            }
            if unknown:
                raise ValueError(
                    f"Unknown system-run task dependencies: {', '.join(sorted(unknown))}"
                )
            raise ValueError("System-run task dependencies contain a cycle")
        ordered.extend(ready)
        resolved.update(task.name for task in ready)
    return tuple(ordered)
