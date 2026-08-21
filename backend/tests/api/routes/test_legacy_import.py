import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.routes import legacy_import as legacy_import_route
from app.core.config import settings
from app.domain import LegacyImportJobStatus
from app.models import LegacyImportJob
from app.use_cases import ledgers as ledger_use_cases
from tests.utils.user import authentication_token_from_email, create_random_user


def test_owner_can_start_legacy_import_job(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner = create_random_user(db)
    headers = authentication_token_from_email(client=client, email=owner.email, db=db)
    ledger = ledger_use_cases.create_ledger(
        session=db, owner_user_id=owner.id, name="Legacy import"
    )
    db.add(
        LegacyImportJob(
            ledger_id=ledger.id,
            status=LegacyImportJobStatus.SUCCEEDED,
            is_active=False,
            processed_obligations=10,
            total_obligations=10,
        )
    )
    db.commit()
    started_jobs: list[object] = []
    monkeypatch.setattr(
        legacy_import_route, "run_legacy_import_job", started_jobs.append
    )

    response = client.post(
        f"{settings.API_V1_STR}/ledgers/{ledger.id}/legacy-import", headers=headers
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "pending"
    assert started_jobs == [uuid.UUID(payload["id"])]

    status_response = client.get(
        f"{settings.API_V1_STR}/ledgers/{ledger.id}/legacy-import",
        headers=headers,
    )
    assert status_response.status_code == 200
    assert status_response.json()["id"] == payload["id"]

    job = db.get(LegacyImportJob, uuid.UUID(payload["id"]))
    assert job is not None
    job.status = LegacyImportJobStatus.SUCCEEDED
    job.is_active = False
    db.commit()


def test_start_legacy_import_rejects_second_active_job(
    client: TestClient, db: Session
) -> None:
    owner = create_random_user(db)
    headers = authentication_token_from_email(client=client, email=owner.email, db=db)
    ledger = ledger_use_cases.create_ledger(
        session=db, owner_user_id=owner.id, name="Legacy import"
    )
    db.add(
        LegacyImportJob(
            ledger_id=ledger.id,
            status=LegacyImportJobStatus.RUNNING,
            is_active=True,
            processed_obligations=100,
            total_obligations=1000,
        )
    )
    db.commit()

    response = client.post(
        f"{settings.API_V1_STR}/ledgers/{ledger.id}/legacy-import", headers=headers
    )

    assert response.status_code == 409


def test_legacy_import_requires_ledger_owner(client: TestClient, db: Session) -> None:
    owner = create_random_user(db)
    outsider = create_random_user(db)
    outsider_headers = authentication_token_from_email(
        client=client, email=outsider.email, db=db
    )
    ledger = ledger_use_cases.create_ledger(
        session=db, owner_user_id=owner.id, name="Legacy import"
    )

    response = client.post(
        f"{settings.API_V1_STR}/ledgers/{ledger.id}/legacy-import",
        headers=outsider_headers,
    )

    assert response.status_code == 404
