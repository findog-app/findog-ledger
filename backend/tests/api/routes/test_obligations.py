from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain import (
    BillingPeriod,
    CurrentValueSource,
    DataSourcePolicy,
    ObligationLifecycle,
    ValueState,
)
from app.use_cases import categories as category_use_cases
from app.use_cases import ledgers as ledger_use_cases
from app.use_cases import obligations as obligation_use_cases
from tests.utils.user import authentication_token_from_email, create_random_user
from tests.utils.utils import random_lower_string


def test_obligations_endpoints_happy_path_and_filters(
    client: TestClient, db: Session
) -> None:
    owner = create_random_user(db)
    headers = authentication_token_from_email(client=client, email=owner.email, db=db)
    ledger = ledger_use_cases.create_ledger(
        session=db, owner_user_id=owner.id, name=f"ledger-{random_lower_string()}"
    )
    category_group = category_use_cases.create_category_group(
        session=db, ledger_id=ledger.id, name=f"group-{random_lower_string()}"
    )
    category_use_cases.create_category(
        session=db,
        ledger_id=ledger.id,
        category_group_id=category_group.id,
        name="Electricity",
        code="ELEC",
    )

    create_response = client.post(
        f"{settings.API_V1_STR}/ledgers/{ledger.id}/obligations",
        headers=headers,
        json={
            "category_code": "ELEC",
            "period": {"year": 2026, "month": 8},
            "data_ready": True,
            "current_amount": "123.45",
            "issue_date": "2026-08-02",
            "due_date": "2026-08-20",
        },
    )

    assert create_response.status_code == 200
    created = create_response.json()
    assert created["key"] == "ELEC-2026-08"
    assert created["category_code"] == "ELEC"
    assert created["period"] == {"year": 2026, "month": 8}
    assert created["lifecycle"] == ObligationLifecycle.READY.value
    assert created["current_amount"] == "123.45"
    assert created["amount_state"] == ValueState.CONFIRMED.value
    assert created["amount_source"] == CurrentValueSource.MANUAL.value
    assert created["issue_date"] == "2026-08-02"
    assert created["issue_date_state"] == ValueState.CONFIRMED.value
    assert created["issue_date_source"] == CurrentValueSource.MANUAL.value
    assert created["due_date"] == "2026-08-20"
    assert created["due_date_state"] == ValueState.CONFIRMED.value
    assert created["due_date_source"] == CurrentValueSource.MANUAL.value

    list_response = client.get(
        f"{settings.API_V1_STR}/ledgers/{ledger.id}/obligations",
        headers=headers,
        params={
            "year": 2026,
            "month": 8,
            "category_code": "ELEC",
            "lifecycle": "ready",
        },
    )

    assert list_response.status_code == 200
    assert list_response.json()["count"] == 1
    assert list_response.json()["data"][0]["key"] == "ELEC-2026-08"

    detail_response = client.get(
        f"{settings.API_V1_STR}/ledgers/{ledger.id}/obligations/ELEC-2026-08",
        headers=headers,
    )

    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == created["id"]


def test_create_obligation_with_incomplete_data_marks_values_as_estimated(
    client: TestClient, db: Session
) -> None:
    owner = create_random_user(db)
    headers = authentication_token_from_email(client=client, email=owner.email, db=db)
    ledger = ledger_use_cases.create_ledger(
        session=db, owner_user_id=owner.id, name=f"ledger-{random_lower_string()}"
    )
    category_group = category_use_cases.create_category_group(
        session=db, ledger_id=ledger.id, name=f"group-{random_lower_string()}"
    )
    category_use_cases.create_category(
        session=db,
        ledger_id=ledger.id,
        category_group_id=category_group.id,
        name="Electricity",
        code="ELEC",
    )

    response = client.post(
        f"{settings.API_V1_STR}/ledgers/{ledger.id}/obligations",
        headers=headers,
        json={
            "category_code": "ELEC",
            "period": {"year": 2026, "month": 8},
            "current_amount": "100.00",
            "issue_date": "2026-08-02",
        },
    )

    assert response.status_code == 200
    created = response.json()
    assert created["lifecycle"] == ObligationLifecycle.COLLECTING_DATA.value
    assert created["amount_state"] == ValueState.ESTIMATED.value
    assert created["amount_source"] == CurrentValueSource.MANUAL.value
    assert created["issue_date_state"] == ValueState.ESTIMATED.value
    assert created["issue_date_source"] == CurrentValueSource.MANUAL.value
    assert created["due_date"] is None
    assert created["due_date_state"] == ValueState.UNKNOWN.value
    assert created["due_date_source"] == CurrentValueSource.UNKNOWN.value


def test_create_ready_obligation_requires_amount_and_due_date(
    client: TestClient, db: Session
) -> None:
    owner = create_random_user(db)
    headers = authentication_token_from_email(client=client, email=owner.email, db=db)
    ledger = ledger_use_cases.create_ledger(
        session=db, owner_user_id=owner.id, name=f"ledger-{random_lower_string()}"
    )
    category_group = category_use_cases.create_category_group(
        session=db, ledger_id=ledger.id, name=f"group-{random_lower_string()}"
    )
    category_use_cases.create_category(
        session=db,
        ledger_id=ledger.id,
        category_group_id=category_group.id,
        name="Electricity",
        code="ELEC",
    )

    response = client.post(
        f"{settings.API_V1_STR}/ledgers/{ledger.id}/obligations",
        headers=headers,
        json={
            "category_code": "ELEC",
            "period": {"year": 2026, "month": 8},
            "data_ready": True,
            "current_amount": "100.00",
        },
    )

    assert response.status_code == 422

    response = client.post(
        f"{settings.API_V1_STR}/ledgers/{ledger.id}/obligations",
        headers=headers,
        json={
            "category_code": "ELEC",
            "period": {"year": 2026, "month": 8},
            "data_ready": True,
            "current_amount": "100.00",
            "issue_date": "2026-08-21",
            "due_date": "2026-08-20",
        },
    )

    assert response.status_code == 422

    response = client.post(
        f"{settings.API_V1_STR}/ledgers/{ledger.id}/obligations",
        headers=headers,
        json={
            "category_code": "ELEC",
            "period": {"year": 2026, "month": 8},
            "data_ready": True,
            "current_amount": "100.00",
            "due_date": "2026-09-11",
        },
    )

    assert response.status_code == 422


def test_create_obligation_rejects_duplicate(client: TestClient, db: Session) -> None:
    owner = create_random_user(db)
    headers = authentication_token_from_email(client=client, email=owner.email, db=db)
    ledger = ledger_use_cases.create_ledger(
        session=db, owner_user_id=owner.id, name=f"ledger-{random_lower_string()}"
    )
    category_group = category_use_cases.create_category_group(
        session=db, ledger_id=ledger.id, name=f"group-{random_lower_string()}"
    )
    category_use_cases.create_category(
        session=db,
        ledger_id=ledger.id,
        category_group_id=category_group.id,
        name="Electricity",
        code="ELEC",
    )
    payload = {"category_code": "ELEC", "period": {"year": 2026, "month": 8}}

    assert (
        client.post(
            f"{settings.API_V1_STR}/ledgers/{ledger.id}/obligations",
            headers=headers,
            json=payload,
        ).status_code
        == 200
    )
    response = client.post(
        f"{settings.API_V1_STR}/ledgers/{ledger.id}/obligations",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Obligation already exists"}


def test_create_obligation_rejects_automatic_category(
    client: TestClient, db: Session
) -> None:
    owner = create_random_user(db)
    headers = authentication_token_from_email(client=client, email=owner.email, db=db)
    ledger = ledger_use_cases.create_ledger(
        session=db, owner_user_id=owner.id, name=f"ledger-{random_lower_string()}"
    )
    category_group = category_use_cases.create_category_group(
        session=db, ledger_id=ledger.id, name=f"group-{random_lower_string()}"
    )
    category_use_cases.create_category(
        session=db,
        ledger_id=ledger.id,
        category_group_id=category_group.id,
        name="Electricity",
        code="ELEC",
        data_source_policy=DataSourcePolicy.AUTOMATIC,
    )

    response = client.post(
        f"{settings.API_V1_STR}/ledgers/{ledger.id}/obligations",
        headers=headers,
        json={"category_code": "ELEC", "period": {"year": 2026, "month": 8}},
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Manual obligations are not allowed for automatic categories"
    }


def test_read_obligation_rejects_invalid_business_key(
    client: TestClient, db: Session
) -> None:
    owner = create_random_user(db)
    headers = authentication_token_from_email(client=client, email=owner.email, db=db)
    ledger = ledger_use_cases.create_ledger(
        session=db, owner_user_id=owner.id, name=f"ledger-{random_lower_string()}"
    )

    response = client.get(
        f"{settings.API_V1_STR}/ledgers/{ledger.id}/obligations/ELEC-2026-13",
        headers=headers,
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid obligation key"}


def test_create_obligation_returns_404_for_missing_category(
    client: TestClient, db: Session
) -> None:
    owner = create_random_user(db)
    headers = authentication_token_from_email(client=client, email=owner.email, db=db)
    ledger = ledger_use_cases.create_ledger(
        session=db, owner_user_id=owner.id, name=f"ledger-{random_lower_string()}"
    )

    response = client.post(
        f"{settings.API_V1_STR}/ledgers/{ledger.id}/obligations",
        headers=headers,
        json={"category_code": "MISS", "period": {"year": 2026, "month": 8}},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Category not found"}


def test_obligation_category_and_lookup_are_scoped_to_ledger(
    client: TestClient, db: Session
) -> None:
    owner = create_random_user(db)
    headers = authentication_token_from_email(client=client, email=owner.email, db=db)
    ledger_one = ledger_use_cases.create_ledger(
        session=db, owner_user_id=owner.id, name=f"ledger-{random_lower_string()}"
    )
    ledger_two = ledger_use_cases.create_ledger(
        session=db, owner_user_id=owner.id, name=f"ledger-{random_lower_string()}"
    )
    group_two = category_use_cases.create_category_group(
        session=db, ledger_id=ledger_two.id, name=f"group-{random_lower_string()}"
    )
    category_use_cases.create_category(
        session=db,
        ledger_id=ledger_two.id,
        category_group_id=group_two.id,
        name="Gas",
        code="GASS",
    )
    obligation_use_cases.create_manual_obligation(
        session=db,
        ledger_id=ledger_two.id,
        category_code="GASS",
        period=BillingPeriod(2026, 8),
    )

    create_response = client.post(
        f"{settings.API_V1_STR}/ledgers/{ledger_one.id}/obligations",
        headers=headers,
        json={"category_code": "GASS", "period": {"year": 2026, "month": 8}},
    )
    detail_response = client.get(
        f"{settings.API_V1_STR}/ledgers/{ledger_one.id}/obligations/GASS-2026-08",
        headers=headers,
    )

    assert create_response.status_code == 404
    assert create_response.json() == {"detail": "Category not found"}
    assert detail_response.status_code == 404
    assert detail_response.json() == {"detail": "Obligation not found"}


def test_obligation_endpoints_require_authentication(
    client: TestClient, db: Session
) -> None:
    owner = create_random_user(db)
    ledger = ledger_use_cases.create_ledger(
        session=db, owner_user_id=owner.id, name=f"ledger-{random_lower_string()}"
    )

    response = client.get(f"{settings.API_V1_STR}/ledgers/{ledger.id}/obligations")

    assert response.status_code == 401
