import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain import LedgerAccessRole
from app.models import LedgerMembership
from app.use_cases import ledgers as ledger_use_cases
from tests.utils.user import authentication_token_from_email, create_random_user
from tests.utils.utils import random_lower_string


def test_get_ledgers_returns_owned_and_shared_ledgers(
    client: TestClient,
    db: Session,
) -> None:
    owner = create_random_user(db)
    shared_user = create_random_user(db)
    shared_headers = authentication_token_from_email(
        client=client, email=shared_user.email, db=db
    )
    owned_ledger = ledger_use_cases.create_ledger(
        session=db,
        owner_user_id=shared_user.id,
        name=f"owned-{random_lower_string()}",
    )
    shared_ledger = ledger_use_cases.create_ledger(
        session=db,
        owner_user_id=owner.id,
        name=f"shared-{random_lower_string()}",
    )
    ledger_use_cases.share_ledger(
        session=db,
        ledger_id=shared_ledger.id,
        target_user_id=shared_user.id,
        role=LedgerAccessRole.VIEWER,
    )

    response = client.get(f"{settings.API_V1_STR}/ledgers/", headers=shared_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 2
    assert {item["id"] for item in payload["data"]} == {
        str(owned_ledger.id),
        str(shared_ledger.id),
    }


def test_post_ledgers_creates_ledger_and_owner_membership(
    client: TestClient,
    db: Session,
) -> None:
    user = create_random_user(db)
    headers = authentication_token_from_email(client=client, email=user.email, db=db)

    response = client.post(
        f"{settings.API_V1_STR}/ledgers/",
        headers=headers,
        json={"name": f"ledger-{random_lower_string()}", "description": "Primary"},
    )

    assert response.status_code == 200
    payload = response.json()
    membership = db.get(
        LedgerMembership,
        {"ledger_id": uuid.UUID(payload["id"]), "user_id": user.id},
    )
    assert payload["owner_user_id"] == str(user.id)
    assert membership is not None
    assert membership.role == LedgerAccessRole.OWNER


def test_get_ledger_returns_404_for_non_member(client: TestClient, db: Session) -> None:
    owner = create_random_user(db)
    outsider = create_random_user(db)
    outsider_headers = authentication_token_from_email(
        client=client, email=outsider.email, db=db
    )
    ledger = ledger_use_cases.create_ledger(
        session=db,
        owner_user_id=owner.id,
        name=f"ledger-{random_lower_string()}",
    )

    response = client.get(
        f"{settings.API_V1_STR}/ledgers/{ledger.id}",
        headers=outsider_headers,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Ledger not found"}


def test_get_ledger_members_returns_members_for_authorized_user(
    client: TestClient,
    db: Session,
) -> None:
    owner = create_random_user(db)
    viewer = create_random_user(db)
    viewer_headers = authentication_token_from_email(
        client=client, email=viewer.email, db=db
    )
    ledger = ledger_use_cases.create_ledger(
        session=db,
        owner_user_id=owner.id,
        name=f"ledger-{random_lower_string()}",
    )
    ledger_use_cases.share_ledger(
        session=db,
        ledger_id=ledger.id,
        target_user_id=viewer.id,
        role=LedgerAccessRole.VIEWER,
    )

    response = client.get(
        f"{settings.API_V1_STR}/ledgers/{ledger.id}/members",
        headers=viewer_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 2
    roles = {item["user_id"]: item["role"] for item in payload["data"]}
    assert roles[str(owner.id)] == "owner"
    assert roles[str(viewer.id)] == "viewer"


def test_post_ledger_members_allows_owner_to_share(
    client: TestClient,
    db: Session,
) -> None:
    owner = create_random_user(db)
    target = create_random_user(db)
    owner_headers = authentication_token_from_email(
        client=client, email=owner.email, db=db
    )
    ledger = ledger_use_cases.create_ledger(
        session=db,
        owner_user_id=owner.id,
        name=f"ledger-{random_lower_string()}",
    )

    response = client.post(
        f"{settings.API_V1_STR}/ledgers/{ledger.id}/members",
        headers=owner_headers,
        json={"user_id": str(target.id), "role": "viewer"},
    )

    assert response.status_code == 200
    payload = response.json()
    membership = db.get(
        LedgerMembership,
        {"ledger_id": ledger.id, "user_id": target.id},
    )
    assert payload["user_id"] == str(target.id)
    assert payload["role"] == "viewer"
    assert membership is not None


def test_post_ledger_members_rejects_non_owner(
    client: TestClient,
    db: Session,
) -> None:
    owner = create_random_user(db)
    editor = create_random_user(db)
    target = create_random_user(db)
    editor_headers = authentication_token_from_email(
        client=client, email=editor.email, db=db
    )
    ledger = ledger_use_cases.create_ledger(
        session=db,
        owner_user_id=owner.id,
        name=f"ledger-{random_lower_string()}",
    )
    ledger_use_cases.share_ledger(
        session=db,
        ledger_id=ledger.id,
        target_user_id=editor.id,
        role=LedgerAccessRole.EDITOR,
    )

    response = client.post(
        f"{settings.API_V1_STR}/ledgers/{ledger.id}/members",
        headers=editor_headers,
        json={"user_id": str(target.id), "role": "viewer"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Ledger not found"}


def test_post_ledger_members_returns_404_for_non_member_access(
    client: TestClient,
    db: Session,
) -> None:
    owner = create_random_user(db)
    outsider = create_random_user(db)
    target = create_random_user(db)
    outsider_headers = authentication_token_from_email(
        client=client, email=outsider.email, db=db
    )
    ledger = ledger_use_cases.create_ledger(
        session=db,
        owner_user_id=owner.id,
        name=f"ledger-{random_lower_string()}",
    )

    response = client.post(
        f"{settings.API_V1_STR}/ledgers/{ledger.id}/members",
        headers=outsider_headers,
        json={"user_id": str(target.id), "role": "viewer"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Ledger not found"}
