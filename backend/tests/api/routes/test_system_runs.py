from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain import TaskRunMode
from app.domain.system_run import SystemRunStatus, SystemRunTrigger
from app.models import SystemRun
from tests.utils.user import authentication_token_from_email, create_random_user


def test_system_runs_require_a_superuser(client: TestClient, db: Session) -> None:
    user = create_random_user(db)
    headers = authentication_token_from_email(client=client, email=user.email, db=db)

    response = client.get(f"{settings.API_V1_STR}/system-runs/", headers=headers)

    assert response.status_code == 403


def test_administrator_can_start_manual_run_and_inspect_history(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "LEGACY_IMPORT_MODE", TaskRunMode.MANUAL_ONLY)
    started = client.post(
        f"{settings.API_V1_STR}/system-runs/", headers=superuser_token_headers
    )

    assert started.status_code == 200
    run = started.json()
    assert run["trigger"] == "manual"
    assert run["status"] == "success"
    assert any(step["skip_reason"] == "manual_only" for step in run["steps"])

    history = client.get(
        f"{settings.API_V1_STR}/system-runs/", headers=superuser_token_headers
    )
    assert history.status_code == 200
    assert history.json()["data"][0]["id"] == run["id"]

    details = client.get(
        f"{settings.API_V1_STR}/system-runs/{run['id']}",
        headers=superuser_token_headers,
    )
    assert details.status_code == 200
    assert details.json()["steps"] == run["steps"]


def test_manual_only_task_requires_explicit_selection(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "LEGACY_IMPORT_MODE", TaskRunMode.MANUAL_ONLY)

    response = client.post(
        f"{settings.API_V1_STR}/system-runs/",
        headers=superuser_token_headers,
        json={"task_names": ["legacy_import"]},
    )

    assert response.status_code == 200
    assert [step["task_name"] for step in response.json()["steps"]] == ["legacy_import"]
    assert response.json()["steps"][0]["skip_reason"] == "not_configured"


def test_disabled_tasks_cannot_be_started_manually(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "LEGACY_IMPORT_MODE", TaskRunMode.DISABLED)

    response = client.post(
        f"{settings.API_V1_STR}/system-runs/",
        headers=superuser_token_headers,
        json={"task_names": ["legacy_import"]},
    )

    assert response.status_code == 409
    assert (
        response.json()["detail"] == "Disabled tasks cannot be started: legacy_import"
    )


def test_start_reports_an_already_running_execution(
    client: TestClient, db: Session, superuser_token_headers: dict[str, str]
) -> None:
    now = datetime.now(UTC)
    active = SystemRun(
        status=SystemRunStatus.RUNNING,
        trigger=SystemRunTrigger.SCHEDULED,
        effective_at=now,
        timezone="UTC",
        business_date=now.date(),
        started_at=now,
    )
    db.add(active)
    db.commit()

    response = client.post(
        f"{settings.API_V1_STR}/system-runs/", headers=superuser_token_headers
    )

    assert response.status_code == 409
    assert str(active.id) in response.json()["detail"]
