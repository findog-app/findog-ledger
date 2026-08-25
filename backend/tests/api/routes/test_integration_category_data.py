from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.use_cases import categories as category_use_cases
from tests.utils.ledger_domain import create_category_tree
from tests.utils.user import authentication_token_from_email


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
