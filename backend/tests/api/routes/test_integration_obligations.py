import uuid
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain import (
    BillingPeriod,
    CurrentValueSource,
    ObligationKey,
    ObligationLifecycle,
)
from app.use_cases import categories as category_use_cases
from app.use_cases import ledgers as ledger_use_cases
from app.use_cases import obligations as obligation_use_cases
from tests.utils.user import authentication_token_from_email, create_random_user


def _api_key(
    client: TestClient, headers: dict[str, str], ledger_id: str, scopes: list[str]
) -> dict[str, object]:
    response = client.post(
        f"{settings.API_V1_STR}/ledgers/{ledger_id}/api-keys",
        headers=headers,
        json={"name": "enea-importer", "scopes": scopes},
    )
    assert response.status_code == 200
    return response.json()


def _ledger_with_obligation(db: Session, *, owner_id: uuid.UUID, code: str = "ELEC"):
    ledger = ledger_use_cases.create_ledger(
        session=db, owner_user_id=owner_id, name=f"Ledger {code}"
    )
    group = category_use_cases.create_category_group(
        session=db, ledger_id=ledger.id, name=f"Group {code}"
    )
    category_use_cases.create_category(
        session=db,
        ledger_id=ledger.id,
        category_group_id=group.id,
        name=f"Category {code}",
        code=code,
    )
    obligation = obligation_use_cases.create_manual_obligation(
        session=db,
        ledger_id=ledger.id,
        category_code=code,
        period=BillingPeriod(2026, 8),
    )
    return ledger, obligation


def test_integration_obligations_are_ledger_scoped_and_use_integration_sources(
    client: TestClient, db: Session
) -> None:
    owner = create_random_user(db)
    jwt_headers = authentication_token_from_email(
        client=client, email=owner.email, db=db
    )
    ledger, obligation = _ledger_with_obligation(db, owner_id=owner.id)
    other_ledger, other_obligation = _ledger_with_obligation(
        db, owner_id=owner.id, code="GASS"
    )
    read_key = _api_key(client, jwt_headers, str(ledger.id), ["ledger:read"])
    write_key = _api_key(client, jwt_headers, str(ledger.id), ["ledger:write"])
    read_headers = {"Authorization": f"Bearer {read_key['key']}"}
    write_headers = {"Authorization": f"Bearer {write_key['key']}"}

    response = client.get(
        f"{settings.API_V1_STR}/integration/obligations",
        headers=read_headers,
        params={"year": 2026, "month": 8, "category_code": "ELEC"},
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["data"][0]["key"] == obligation.business_key

    response = client.get(
        f"{settings.API_V1_STR}/integration/obligations/{other_obligation.business_key}",
        headers=read_headers,
    )
    assert response.status_code == 404
    assert other_ledger.id != ledger.id

    response = client.patch(
        f"{settings.API_V1_STR}/integration/obligations/{obligation.business_key}",
        headers=read_headers,
        json={"current_amount": "123.45"},
    )
    assert response.status_code == 403

    response = client.patch(
        f"{settings.API_V1_STR}/integration/obligations/{obligation.business_key}",
        headers=write_headers,
        json={
            "current_amount": "123.45",
            "issue_date": "2026-08-02",
            "due_date": "2026-08-20",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["amount_source"] == CurrentValueSource.INTEGRATION.value
    assert payload["issue_date_source"] == CurrentValueSource.INTEGRATION.value
    assert payload["due_date_source"] == CurrentValueSource.INTEGRATION.value
    assert payload["effective_value_source"] == "integration"


def test_integration_obligation_lifecycle_actions_and_append_only_notes(
    client: TestClient, db: Session
) -> None:
    owner = create_random_user(db)
    jwt_headers = authentication_token_from_email(
        client=client, email=owner.email, db=db
    )
    ledger, obligation = _ledger_with_obligation(db, owner_id=owner.id)
    key = _api_key(client, jwt_headers, str(ledger.id), ["ledger:write"])
    headers = {"Authorization": f"Bearer {key['key']}"}
    url = f"{settings.API_V1_STR}/integration/obligations/{obligation.business_key}"

    response = client.patch(
        url,
        headers=headers,
        json={"current_amount": "80", "due_date": "2026-08-20"},
    )
    assert response.status_code == 200
    response = client.patch(f"{url}/ready", headers=headers)
    assert response.status_code == 200
    assert response.json()["lifecycle"] == ObligationLifecycle.READY.value
    response = client.post(f"{url}/mark-paid", headers=headers)
    assert response.status_code == 200
    assert response.json()["lifecycle"] == ObligationLifecycle.PAID.value
    response = client.post(f"{url}/reopen", headers=headers)
    assert response.status_code == 200
    response = client.post(f"{url}/cancel", headers=headers)
    assert response.status_code == 200
    response = client.post(f"{url}/reopen", headers=headers)
    assert response.status_code == 200
    response = client.post(f"{url}/error", headers=headers)
    assert response.status_code == 200
    assert response.json()["lifecycle"] == ObligationLifecycle.ERROR.value

    response = client.post(
        f"{url}/notes", headers=headers, json={"text": "First failure"}
    )
    assert response.status_code == 200
    assert response.json()["notes"].endswith("enea-importer: First failure")
    response = client.post(
        f"{url}/notes", headers=headers, json={"text": "Second failure"}
    )
    assert response.status_code == 200
    notes = response.json()["notes"]
    assert notes.count("enea-importer:") == 2
    assert "First failure\n" in notes

    response = client.post(f"{url}/mark-paid", headers=headers)
    assert response.status_code == 409


def test_integration_and_manual_values_have_mixed_effective_source(
    client: TestClient, db: Session
) -> None:
    owner = create_random_user(db)
    jwt_headers = authentication_token_from_email(
        client=client, email=owner.email, db=db
    )
    ledger, obligation = _ledger_with_obligation(db, owner_id=owner.id)
    obligation = obligation_use_cases.update_manual_obligation(
        session=db,
        ledger_id=ledger.id,
        key=ObligationKey.parse(obligation.business_key),
        due_date=date(2026, 8, 20),
    )
    key = _api_key(client, jwt_headers, str(ledger.id), ["ledger:write"])

    response = client.patch(
        f"{settings.API_V1_STR}/integration/obligations/{obligation.business_key}",
        headers={"Authorization": f"Bearer {key['key']}"},
        json={"current_amount": "80"},
    )

    assert response.status_code == 200
    assert response.json()["effective_value_source"] == "mixed"
