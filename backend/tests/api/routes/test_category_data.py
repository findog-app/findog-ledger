from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.use_cases import categories as category_use_cases
from app.use_cases import ledgers as ledger_use_cases
from tests.utils.user import authentication_token_from_email, create_random_user
from tests.utils.utils import random_lower_string


def test_category_data_api_validates_payload_and_returns_schema_version(
    client: TestClient, db: Session
) -> None:
    owner = create_random_user(db)
    headers = authentication_token_from_email(client=client, email=owner.email, db=db)
    ledger = ledger_use_cases.create_ledger(
        session=db, owner_user_id=owner.id, name=f"ledger-{random_lower_string()}"
    )
    group = category_use_cases.create_category_group(
        session=db, ledger_id=ledger.id, name="Utilities"
    )
    category = category_use_cases.create_category(
        session=db,
        ledger_id=ledger.id,
        category_group_id=group.id,
        name="Electricity",
        code="ELEC",
    )
    schema_url = f"{settings.API_V1_STR}/ledgers/{ledger.id}/categories/{category.id}/data-schema"
    data_url = (
        f"{settings.API_V1_STR}/ledgers/{ledger.id}/categories/{category.id}/data"
    )
    schema_response = client.post(
        schema_url,
        headers=headers,
        json={
            "schema": {
                "type": "object",
                "properties": {"invoice_available": {"type": "boolean"}},
                "required": ["invoice_available"],
                "additionalProperties": False,
            }
        },
    )
    valid_response = client.put(
        data_url, headers=headers, json={"data": {"invoice_available": True}}
    )
    invalid_response = client.put(
        data_url, headers=headers, json={"data": {"unexpected": True}}
    )

    assert schema_response.status_code == 200
    assert schema_response.json()["version"] == 1
    assert valid_response.status_code == 200
    assert valid_response.json()["schema_version"] == 1
    assert valid_response.json()["data"] == {"invoice_available": True}
    assert invalid_response.status_code == 422
