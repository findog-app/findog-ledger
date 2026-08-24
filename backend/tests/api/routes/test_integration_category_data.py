import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.use_cases import categories as category_use_cases
from app.use_cases import ledgers as ledger_use_cases
from tests.utils.user import authentication_token_from_email, create_random_user


def _api_key(
    client: TestClient, headers: dict[str, str], ledger_id: uuid.UUID, scopes: list[str]
) -> dict[str, object]:
    response = client.post(
        f"{settings.API_V1_STR}/ledgers/{ledger_id}/api-keys",
        headers=headers,
        json={"name": "meter-importer", "scopes": scopes},
    )
    assert response.status_code == 200
    return response.json()


def _category(
    db: Session, owner_id: uuid.UUID, code: str, ledger_name: str | None = None
):
    ledger = ledger_use_cases.create_ledger(
        session=db,
        owner_user_id=owner_id,
        name=f"Ledger {ledger_name or code}",
    )
    group = category_use_cases.create_category_group(
        session=db, ledger_id=ledger.id, name=f"Group {code}"
    )
    category = category_use_cases.create_category(
        session=db,
        ledger_id=ledger.id,
        category_group_id=group.id,
        name=f"Category {code}",
        code=code,
    )
    category_use_cases.set_category_data_schema(
        session=db,
        ledger_id=ledger.id,
        category_id=category.id,
        schema={
            "type": "object",
            "properties": {
                "invoice_available": {"type": "boolean"},
                "meter_reading_kwh": {"type": "number"},
            },
            "required": ["invoice_available", "meter_reading_kwh"],
            "additionalProperties": False,
        },
    )
    return ledger, category


def test_integration_category_data_patch_is_ledger_scoped_and_validates_merged_data(
    client: TestClient, db: Session
) -> None:
    owner = create_random_user(db)
    jwt_headers = authentication_token_from_email(
        client=client, email=owner.email, db=db
    )
    ledger, category = _category(db, owner.id, "ELEC")
    _category(db, owner.id, "ELEC", ledger_name="Other ELEC")
    _, foreign_category = _category(db, owner.id, "GASS")
    key = _api_key(client, jwt_headers, ledger.id, ["ledger:read", "ledger:write"])
    headers = {"Authorization": f"Bearer {key['key']}"}
    data_url = f"{settings.API_V1_STR}/integration/categories/{category.code}/data"

    response = client.patch(
        data_url,
        headers=headers,
        json={"invoice_available": True},
    )
    assert response.status_code == 422

    response = client.patch(
        data_url,
        headers=headers,
        json={"invoice_available": True, "meter_reading_kwh": 12401.2},
    )
    assert response.status_code == 200
    assert response.json()["data"]["meter_reading_kwh"] == 12401.2

    response = client.patch(
        data_url,
        headers=headers,
        json={"meter_reading_kwh": 12402.7},
    )
    assert response.status_code == 200
    assert response.json()["data"] == {
        "invoice_available": True,
        "meter_reading_kwh": 12402.7,
    }

    response = client.get(data_url, headers=headers)
    assert response.status_code == 200
    assert response.json()["data"]["meter_reading_kwh"] == 12402.7

    response = client.get(
        f"{settings.API_V1_STR}/integration/categories/{category.code}/data-schema",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["schema"]["properties"]["meter_reading_kwh"] == {
        "type": "number"
    }

    # Another ledger also has ELEC; the successful requests above resolve to the
    # API key's ledger. A code that exists only in a different ledger is hidden.
    response = client.get(
        f"{settings.API_V1_STR}/integration/categories/{foreign_category.code}/data-schema",
        headers=headers,
    )
    assert response.status_code == 404

    response = client.get(
        f"{settings.API_V1_STR}/integration/categories/MISS/data-schema",
        headers=headers,
    )
    assert response.status_code == 404


def test_integration_category_data_requires_matching_scope(
    client: TestClient, db: Session
) -> None:
    owner = create_random_user(db)
    jwt_headers = authentication_token_from_email(
        client=client, email=owner.email, db=db
    )
    ledger, category = _category(db, owner.id, "ELEC")
    read_key = _api_key(client, jwt_headers, ledger.id, ["ledger:read"])
    headers = {"Authorization": f"Bearer {read_key['key']}"}

    response = client.patch(
        f"{settings.API_V1_STR}/integration/categories/{category.code}/data",
        headers=headers,
        json={"invoice_available": True, "meter_reading_kwh": 12401.2},
    )
    assert response.status_code == 403
