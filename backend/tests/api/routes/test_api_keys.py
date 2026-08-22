from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import ApiKey
from app.use_cases import ledgers as ledger_use_cases
from tests.utils.user import authentication_token_from_email, create_random_user


def _create_key(
    client: TestClient, headers: dict[str, str], ledger_id: str, *, scopes: list[str]
) -> dict[str, object]:
    response = client.post(
        f"{settings.API_V1_STR}/ledgers/{ledger_id}/api-keys",
        headers=headers,
        json={"name": "Test integration", "scopes": scopes},
    )
    assert response.status_code == 200
    return response.json()


def test_creates_api_key_without_persisting_raw_secret(
    client: TestClient, db: Session
) -> None:
    owner = create_random_user(db)
    headers = authentication_token_from_email(client=client, email=owner.email, db=db)
    ledger = ledger_use_cases.create_ledger(
        session=db, owner_user_id=owner.id, name="One"
    )

    payload = _create_key(client, headers, str(ledger.id), scopes=["ledger:read"])

    assert payload["key"].startswith("fdg_live_")
    assert payload["key_prefix"] == payload["key"][:16]
    stored_key = db.get(ApiKey, payload["id"])
    assert stored_key is not None
    assert stored_key.key_hash != payload["key"]
    assert payload["key"] not in stored_key.key_hash


def test_integration_key_is_ledger_scoped_and_requires_read_scope(
    client: TestClient, db: Session
) -> None:
    owner = create_random_user(db)
    headers = authentication_token_from_email(client=client, email=owner.email, db=db)
    ledger = ledger_use_cases.create_ledger(
        session=db, owner_user_id=owner.id, name="One"
    )
    other = ledger_use_cases.create_ledger(
        session=db, owner_user_id=owner.id, name="Two"
    )
    payload = _create_key(client, headers, str(ledger.id), scopes=["ledger:read"])

    response = client.get(
        f"{settings.API_V1_STR}/integration/ledger?ledger_id={other.id}",
        headers={"Authorization": f"Bearer {payload['key']}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(ledger.id)
    stored_key = db.get(ApiKey, payload["id"])
    assert stored_key is not None
    db.refresh(stored_key)
    assert stored_key.last_used_at is not None

    response = client.get(
        f"{settings.API_V1_STR}/integration/ledger",
        headers={"Authorization": "Bearer fdg_live_invalid"},
    )
    assert response.status_code == 401


def test_integration_key_rejects_missing_scope_expiry_and_revocation(
    client: TestClient, db: Session
) -> None:
    owner = create_random_user(db)
    headers = authentication_token_from_email(client=client, email=owner.email, db=db)
    ledger = ledger_use_cases.create_ledger(
        session=db, owner_user_id=owner.id, name="One"
    )
    write_key = _create_key(client, headers, str(ledger.id), scopes=["ledger:write"])

    response = client.get(
        f"{settings.API_V1_STR}/integration/ledger",
        headers={"Authorization": f"Bearer {write_key['key']}"},
    )
    assert response.status_code == 403

    response = client.patch(
        f"{settings.API_V1_STR}/integration/ledger",
        headers={"Authorization": f"Bearer {write_key['key']}"},
        json={"name": "Renamed", "description": "Updated through integration"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"

    stored_key = db.get(ApiKey, write_key["id"])
    assert stored_key is not None
    stored_key.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    response = client.get(
        f"{settings.API_V1_STR}/integration/ledger",
        headers={"Authorization": f"Bearer {write_key['key']}"},
    )
    assert response.status_code == 401

    stored_key.expires_at = None
    db.commit()
    revoke_response = client.delete(
        f"{settings.API_V1_STR}/ledgers/{ledger.id}/api-keys/{write_key['id']}",
        headers=headers,
    )
    assert revoke_response.status_code == 200
    response = client.get(
        f"{settings.API_V1_STR}/integration/ledger",
        headers={"Authorization": f"Bearer {write_key['key']}"},
    )
    assert response.status_code == 401
