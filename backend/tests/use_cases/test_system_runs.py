from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import TaskRunMode
from app.domain.system_run import (
    SystemRunSkipReason,
    SystemRunStatus,
    SystemRunStepStatus,
)
from app.models import Ledger, Obligation, SystemRunStep
from app.use_cases import ledgers as ledger_use_cases
from app.use_cases.system_runs import EnsureObligationsTask, SystemRunOrchestrator
from tests.utils.ledger_domain import create_category_with_recurrence
from tests.utils.user import create_random_user


class FakeTask:
    def __init__(
        self,
        name: str,
        *,
        mode: TaskRunMode = TaskRunMode.SCHEDULED,
        dependencies: tuple[str, ...] = (),
        configured: bool = True,
        due: bool = True,
        failing_ledger_ids: set[object] | None = None,
    ) -> None:
        self.name = name
        self.mode = mode
        self.dependencies = dependencies
        self.configured = configured
        self.due = due
        self.failing_ledger_ids = failing_ledger_ids or set()
        self.calls: list[object] = []

    def is_configured(self) -> bool:
        return self.configured

    def is_due(self, run_at: datetime) -> bool:
        return self.due

    def run(self, *, session: Session, ledger: Ledger, run_at: datetime) -> None:
        self.calls.append(ledger.id)
        if ledger.id in self.failing_ledger_ids:
            raise RuntimeError(f"failed {ledger.id}")


def _ledger(db: Session, name: str) -> Ledger:
    user = create_random_user(db)
    return ledger_use_cases.create_ledger(session=db, owner_user_id=user.id, name=name)


def _steps(db: Session, run_id: object) -> list[SystemRunStep]:
    return list(
        db.scalars(
            select(SystemRunStep)
            .where(SystemRunStep.system_run_id == run_id)
            .order_by(SystemRunStep.task_name, SystemRunStep.ledger_id)
        )
    )


def test_orchestrator_orders_tasks_and_continues_independent_ledgers(
    db: Session,
) -> None:
    first = _ledger(db, "First")
    second = _ledger(db, "Second")
    prerequisite = FakeTask("prerequisite", failing_ledger_ids={first.id})
    dependent = FakeTask("dependent", dependencies=("prerequisite",))
    independent = FakeTask("independent")

    run = SystemRunOrchestrator((dependent, independent, prerequisite)).run(
        session=db, run_at=datetime(2026, 8, 1, tzinfo=UTC)
    )

    assert run.status is SystemRunStatus.PARTIAL_FAILURE
    assert prerequisite.calls == [first.id, second.id]
    assert dependent.calls == [second.id]
    assert independent.calls == [first.id, second.id]
    steps = _steps(db, run.id)
    skipped = next(
        step
        for step in steps
        if step.task_name == "dependent" and step.ledger_id == first.id
    )
    assert skipped.status is SystemRunStepStatus.SKIPPED
    assert skipped.skip_reason is SystemRunSkipReason.PREREQUISITE_FAILED


def test_orchestrator_persists_mode_and_eligibility_skip_reasons(db: Session) -> None:
    disabled = FakeTask("disabled", mode=TaskRunMode.DISABLED)
    manual = FakeTask("manual", mode=TaskRunMode.MANUAL_ONLY)
    not_configured = FakeTask("not-configured", configured=False)
    not_due = FakeTask("not-due", due=False)

    run = SystemRunOrchestrator((disabled, manual, not_configured, not_due)).run(
        session=db, run_at=datetime(2026, 8, 1, tzinfo=UTC)
    )

    assert run.status is SystemRunStatus.SUCCESS
    assert {(step.task_name, step.skip_reason) for step in _steps(db, run.id)} == {
        ("disabled", SystemRunSkipReason.DISABLED),
        ("manual", SystemRunSkipReason.MANUAL_ONLY),
        ("not-configured", SystemRunSkipReason.NOT_CONFIGURED),
        ("not-due", SystemRunSkipReason.NOT_DUE),
    }


def test_orchestrator_records_no_eligible_targets(db: Session) -> None:
    run = SystemRunOrchestrator((FakeTask("scheduled"),)).run(session=db)

    step = _steps(db, run.id)[0]
    assert step.status is SystemRunStepStatus.SKIPPED
    assert step.skip_reason is SystemRunSkipReason.NO_ELIGIBLE_TARGETS


def test_manual_only_task_requires_explicit_selection(db: Session) -> None:
    ledger = _ledger(db, "Manual")
    manual = FakeTask("manual", mode=TaskRunMode.MANUAL_ONLY)
    orchestrator = SystemRunOrchestrator((manual,))

    implicit = orchestrator.run(session=db)
    explicit = orchestrator.run(session=db, task_names=("manual",))

    assert _steps(db, implicit.id)[0].skip_reason is SystemRunSkipReason.MANUAL_ONLY
    assert manual.calls == [ledger.id]
    assert _steps(db, explicit.id)[0].status is SystemRunStepStatus.SUCCEEDED


def test_ensure_task_is_safe_to_retry(db: Session) -> None:
    ledger, _, _ = create_category_with_recurrence(db)
    orchestrator = SystemRunOrchestrator((EnsureObligationsTask(),))
    run_at = datetime(2026, 8, 1, tzinfo=UTC)

    orchestrator.run(session=db, run_at=run_at)
    orchestrator.run(session=db, run_at=run_at)

    assert (
        len(
            list(
                db.scalars(select(Obligation).where(Obligation.ledger_id == ledger.id))
            )
        )
        == 2
    )
