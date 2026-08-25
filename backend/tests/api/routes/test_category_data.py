from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.use_cases import categories as category_use_cases
from tests.utils.ledger_domain import create_category_tree
from tests.utils.user import authentication_token_from_email


def test_category_data_records_api_lists_and_reads_latest(
    client: TestClient, db: Session
) -> None:
    ledger, _, category = create_category_tree(db)
    headers = authentication_token_from_email(
        client=client, email=ledger.owner.email, db=db
    )
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
    category_use_cases.create_category_data_record(
        session=db,
        ledger_id=ledger.id,
        category_id=category.id,
        observed_at=datetime(2026, 1, 1, tzinfo=UTC),
        data={"reading": 1},
    )
    latest = category_use_cases.create_category_data_record(
        session=db,
        ledger_id=ledger.id,
        category_id=category.id,
        observed_at=datetime(2026, 1, 2, tzinfo=UTC),
        data={"reading": 2},
    )

    records_response = client.get(
        f"{settings.API_V1_STR}/ledgers/{ledger.id}/categories/{category.id}/data-records",
        headers=headers,
    )
    latest_response = client.get(
        f"{settings.API_V1_STR}/ledgers/{ledger.id}/categories/{category.id}/data-records/latest",
        headers=headers,
    )

    assert records_response.status_code == 200
    assert records_response.json()["count"] == 2
    assert records_response.json()["data"][0]["data"] == {"reading": 2}
    assert latest_response.status_code == 200
    assert latest_response.json()["id"] == str(latest.id)


def test_category_data_records_api_validates_pagination(
    client: TestClient, db: Session
) -> None:
    ledger, _, category = create_category_tree(db)
    headers = authentication_token_from_email(
        client=client, email=ledger.owner.email, db=db
    )
    url = f"{settings.API_V1_STR}/ledgers/{ledger.id}/categories/{category.id}/data-records"

    invalid_limit = client.get(f"{url}?limit=101", headers=headers)
    invalid_offset = client.get(f"{url}?offset=-1", headers=headers)

    assert invalid_limit.status_code == 422
    assert invalid_offset.status_code == 422
