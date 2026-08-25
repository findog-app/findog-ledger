from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.use_cases import categories as category_use_cases
from app.use_cases import ledgers as ledger_use_cases
from tests.utils.ledger_domain import create_category_tree
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import random_lower_string


def test_integration_category_data_records_are_idempotent(
    client: TestClient, db: Session
) -> None:
    ledger, _, category = create_category_tree(db)
    category_use_cases.set_category_data_schema(
        session=db,
        ledger_id=ledger.id,
        category_id=category.id,
        schema={
            "type": "object",
            "properties": {"reading": {"type": "number"}},
            "required": ["reading"],
            "additionalProperties": False,
        },
    )
    jwt_headers = authentication_token_from_email(
        client=client, email=ledger.owner.email, db=db
    )
    key_response = client.post(
        f"{settings.API_V1_STR}/ledgers/{ledger.id}/api-keys",
        headers=jwt_headers,
        json={"name": "meter", "scopes": ["ledger:write", "ledger:read"]},
    )
    assert key_response.status_code == 200
    headers = {"Authorization": f"Bearer {key_response.json()['key']}"}
    payload = {
        "observed_at": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
        "data": {"reading": 1},
        "source": "meter",
        "external_id": "event-1",
    }

    first = client.post(
        f"{settings.API_V1_STR}/integration/categories/{category.code}/data-records",
        headers=headers,
        json=payload,
    )
    second = client.post(
        f"{settings.API_V1_STR}/integration/categories/{category.code}/data-records",
        headers=headers,
        json=payload,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]


def test_integration_category_data_records_enforce_scopes_and_ledger_isolation(
    client: TestClient, db: Session
) -> None:
    ledger, _, category = create_category_tree(db)
    category_use_cases.set_category_data_schema(
        session=db,
        ledger_id=ledger.id,
        category_id=category.id,
        schema={
            "type": "object",
            "properties": {"reading": {"type": "number"}},
            "required": ["reading"],
            "additionalProperties": False,
        },
    )
    jwt_headers = authentication_token_from_email(
        client=client, email=ledger.owner.email, db=db
    )
    read_key = client.post(
        f"{settings.API_V1_STR}/ledgers/{ledger.id}/api-keys",
        headers=jwt_headers,
        json={"name": "reader", "scopes": ["ledger:read"]},
    ).json()["key"]
    payload = {
        "observed_at": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
        "data": {"reading": 1},
    }
    write_url = (
        f"{settings.API_V1_STR}/integration/categories/{category.code}/data-records"
    )

    forbidden = client.post(
        write_url, headers={"Authorization": f"Bearer {read_key}"}, json=payload
    )

    assert forbidden.status_code == 403

    category_use_cases.create_category_data_record(
        session=db,
        ledger_id=ledger.id,
        category_id=category.id,
        observed_at=datetime(2026, 1, 1, tzinfo=UTC),
        data={"reading": 1},
    )

    other_ledger = ledger_use_cases.create_ledger(
        session=db,
        owner_user_id=ledger.owner_user_id,
        name=f"other-{random_lower_string()}",
    )
    other_group = category_use_cases.create_category_group(
        session=db, ledger_id=other_ledger.id, name="Other group"
    )
    other_category = category_use_cases.create_category(
        session=db,
        ledger_id=other_ledger.id,
        category_group_id=other_group.id,
        name="Other category",
        code=category.code,
    )
    category_use_cases.set_category_data_schema(
        session=db,
        ledger_id=other_ledger.id,
        category_id=other_category.id,
        schema={
            "type": "object",
            "properties": {"reading": {"type": "number"}},
            "required": ["reading"],
            "additionalProperties": False,
        },
    )
    other_key = client.post(
        f"{settings.API_V1_STR}/ledgers/{other_ledger.id}/api-keys",
        headers=jwt_headers,
        json={"name": "other-reader", "scopes": ["ledger:read"]},
    ).json()["key"]

    isolated = client.get(
        f"{settings.API_V1_STR}/integration/categories/{category.code}/data-records",
        headers={"Authorization": f"Bearer {other_key}"},
    )

    assert isolated.status_code == 200
    assert isolated.json() == {"data": [], "count": 0}
