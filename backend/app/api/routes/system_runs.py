import uuid
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import SessionDep, get_current_active_superuser
from app.domain import TaskRunMode
from app.domain.system_run import SystemRunStatus, SystemRunTrigger
from app.models import SystemRun, SystemRunStep
from app.schemas import (
    SystemRunPublic,
    SystemRunsPublic,
    SystemRunStart,
    SystemRunStepPublic,
    SystemRunTaskPublic,
)
from app.use_cases.system_runs import (
    SYSTEM_RUN_TASK_REGISTRY,
    SystemRunContext,
    SystemRunOrchestrator,
)

router = APIRouter(
    prefix="/system-runs",
    tags=["system-runs"],
    dependencies=[Depends(get_current_active_superuser)],
)


def _to_public(session: SessionDep, run: SystemRun) -> SystemRunPublic:
    steps = list(
        session.scalars(
            select(SystemRunStep)
            .where(SystemRunStep.system_run_id == run.id)
            .order_by(SystemRunStep.started_at, SystemRunStep.id)
        )
    )
    return SystemRunPublic(
        id=run.id,
        status=run.status,
        trigger=run.trigger,
        effective_at=run.effective_at,
        timezone=run.timezone,
        business_date=run.business_date,
        summary=run.summary,
        error=run.error,
        started_at=run.started_at,
        finished_at=run.finished_at,
        steps=[SystemRunStepPublic.model_validate(step) for step in steps],
    )


@router.get("/tasks", response_model=list[SystemRunTaskPublic])
def read_system_run_tasks() -> Any:
    return [
        SystemRunTaskPublic(name=task.name, mode=task.mode)
        for task in SYSTEM_RUN_TASK_REGISTRY
    ]


@router.post("/", response_model=SystemRunPublic)
def start_system_run(
    *, session: SessionDep, run_in: SystemRunStart = SystemRunStart()
) -> Any:
    active_run = session.scalar(
        select(SystemRun).where(SystemRun.status == SystemRunStatus.RUNNING)
    )
    if active_run is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"System run {active_run.id} is already running",
        )

    requested = set(run_in.task_names) if run_in.task_names is not None else None
    known_tasks = {task.name: task for task in SYSTEM_RUN_TASK_REGISTRY}
    if requested is not None:
        unknown = requested - known_tasks.keys()
        if unknown:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown system-run tasks: {', '.join(sorted(unknown))}",
            )
        disabled = [
            name for name in requested if known_tasks[name].mode is TaskRunMode.DISABLED
        ]
        if disabled:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Disabled tasks cannot be started: {', '.join(sorted(disabled))}",
            )

    run = SystemRunOrchestrator().run(
        session=session,
        context=SystemRunContext.create(
            effective_at=datetime.now(UTC),
            timezone=ZoneInfo("UTC"),
            trigger=SystemRunTrigger.MANUAL,
        ),
        task_names=requested,
    )
    return _to_public(session, run)


@router.get("/", response_model=SystemRunsPublic)
def read_system_runs(
    *, session: SessionDep, limit: int = Query(default=50, ge=1, le=100)
) -> Any:
    runs = list(
        session.scalars(
            select(SystemRun).order_by(SystemRun.started_at.desc()).limit(limit)
        )
    )
    return SystemRunsPublic(
        data=[_to_public(session, run) for run in runs],
        count=len(runs),
    )


@router.get("/{system_run_id}", response_model=SystemRunPublic)
def read_system_run(*, session: SessionDep, system_run_id: uuid.UUID) -> Any:
    run = session.get(SystemRun, system_run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="System run not found"
        )
    return _to_public(session, run)
