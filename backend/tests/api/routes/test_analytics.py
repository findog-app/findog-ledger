import uuid
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain import BillingPeriod, Currency, ObligationKey, ObligationLifecycle
from app.use_cases import categories as category_use_cases
from app.use_cases import ledgers as ledger_use_cases
from app.use_cases import obligations as obligation_use_cases
from tests.utils.user import authentication_token_from_email, create_random_user
from tests.utils.utils import random_lower_string

PERIOD = BillingPeriod(2026, 8)


def _create_obligation(
    db: Session,
    *,
    ledger_id: uuid.UUID,
    code: str,
    amount: Decimal | None,
    currency: Currency = Currency.PLN,
):
    group = category_use_cases.create_category_group(
        session=db, ledger_id=ledger_id, name=f"group-{code}"
    )
    category_use_cases.create_category(
        session=db,
        ledger_id=ledger_id,
        category_group_id=group.id,
        name=f"Category {code}",
        code=code,
        currency=currency,
    )
    return obligation_use_cases.create_manual_obligation(
        session=db,
        ledger_id=ledger_id,
        category_code=code,
        period=PERIOD,
        data_ready=amount is not None,
        current_amount=amount,
        due_date=date(2026, 8, 20) if amount is not None else None,
    )


def _summary_url(ledger_id: uuid.UUID) -> str:
    return (
        f"{settings.API_V1_STR}/ledgers/{ledger_id}/analytics/period-summary"
        "?year=2026&month=8"
    )


def _create_history_category(
    db: Session, *, ledger_id: uuid.UUID, currency: Currency = Currency.PLN
):
    group = category_use_cases.create_category_group(
        session=db, ledger_id=ledger_id, name=f"group-{random_lower_string()}"
    )
    return category_use_cases.create_category(
        session=db,
        ledger_id=ledger_id,
        category_group_id=group.id,
        name=f"Category {random_lower_string()}",
        code="HIST",
        currency=currency,
    )


def _create_history_obligation(
    db: Session,
    *,
    ledger_id: uuid.UUID,
    category_code: str,
    period: BillingPeriod,
    amount: Decimal | None,
):
    return obligation_use_cases.create_manual_obligation(
        session=db,
        ledger_id=ledger_id,
        category_code=category_code,
        period=period,
        data_ready=amount is not None,
        current_amount=amount,
        due_date=date(period.year, period.month, 20) if amount is not None else None,
    )


@pytest.mark.parametrize(
    ("paid_indexes", "expected_paid_count", "expected_paid_percentage"),
    [({0, 1}, 2, "100"), (set(), 0, "0"), ({0}, 1, "50")],
)
def test_period_summary_reports_all_none_and_partially_paid_obligations(
    client: TestClient,
    db: Session,
    paid_indexes: set[int],
    expected_paid_count: int,
    expected_paid_percentage: str,
) -> None:
    owner = create_random_user(db)
    headers = authentication_token_from_email(client=client, email=owner.email, db=db)
    ledger = ledger_use_cases.create_ledger(
        session=db, owner_user_id=owner.id, name=f"ledger-{random_lower_string()}"
    )
    obligations = [
        _create_obligation(db, ledger_id=ledger.id, code=code, amount=Decimal("50.00"))
        for code in ("PAID", "UNPD")
    ]
    for index in paid_indexes:
        obligation_use_cases.mark_obligation_paid(
            session=db,
            ledger_id=ledger.id,
            key=ObligationKey.parse(obligations[index].business_key),
        )

    response = client.get(_summary_url(ledger.id), headers=headers)

    assert response.status_code == 200
    assert response.json() == {
        "period": {"year": 2026, "month": 8},
        "total_obligation_count": 2,
        "paid_obligation_count": expected_paid_count,
        "paid_percentage": expected_paid_percentage,
        "unknown_amount_count": 0,
        "is_complete": True,
        "amount_summaries": [
            {
                "currency": "PLN",
                "total_known_amount": "100.00",
                "paid_known_amount": f"{expected_paid_count * 50}.00",
                "paid_percentage": expected_paid_percentage,
            }
        ],
    }


def test_period_summary_keeps_unknown_amounts_and_currencies_separate(
    client: TestClient, db: Session
) -> None:
    owner = create_random_user(db)
    headers = authentication_token_from_email(client=client, email=owner.email, db=db)
    ledger = ledger_use_cases.create_ledger(
        session=db, owner_user_id=owner.id, name=f"ledger-{random_lower_string()}"
    )
    paid_pln = _create_obligation(
        db, ledger_id=ledger.id, code="PAID", amount=Decimal("50.00")
    )
    _create_obligation(db, ledger_id=ledger.id, code="UNPD", amount=Decimal("50.00"))
    paid_eur = _create_obligation(
        db,
        ledger_id=ledger.id,
        code="EURO",
        amount=Decimal("20.00"),
        currency=Currency.EUR,
    )
    _create_obligation(db, ledger_id=ledger.id, code="UNKN", amount=None)
    for obligation in (paid_pln, paid_eur):
        obligation_use_cases.mark_obligation_paid(
            session=db,
            ledger_id=ledger.id,
            key=ObligationKey.parse(obligation.business_key),
        )

    other_ledger = ledger_use_cases.create_ledger(
        session=db, owner_user_id=owner.id, name=f"ledger-{random_lower_string()}"
    )
    _create_obligation(
        db, ledger_id=other_ledger.id, code="OTHR", amount=Decimal("999.00")
    )

    response = client.get(_summary_url(ledger.id), headers=headers)

    assert response.status_code == 200
    assert response.json()["total_obligation_count"] == 4
    assert response.json()["paid_obligation_count"] == 2
    assert response.json()["paid_percentage"] == "50"
    assert response.json()["unknown_amount_count"] == 1
    assert response.json()["is_complete"] is False
    assert response.json()["amount_summaries"] == [
        {
            "currency": "EUR",
            "total_known_amount": "20.00",
            "paid_known_amount": "20.00",
            "paid_percentage": "100",
        },
        {
            "currency": "PLN",
            "total_known_amount": "100.00",
            "paid_known_amount": "50.00",
            "paid_percentage": "50",
        },
    ]


def test_period_summary_excludes_canceled_obligations(
    client: TestClient, db: Session
) -> None:
    owner = create_random_user(db)
    headers = authentication_token_from_email(client=client, email=owner.email, db=db)
    ledger = ledger_use_cases.create_ledger(
        session=db, owner_user_id=owner.id, name=f"ledger-{random_lower_string()}"
    )
    paid = _create_obligation(
        db, ledger_id=ledger.id, code="PAID", amount=Decimal("50.00")
    )
    canceled = _create_obligation(
        db, ledger_id=ledger.id, code="CNCL", amount=Decimal("50.00")
    )
    obligation_use_cases.mark_obligation_paid(
        session=db,
        ledger_id=ledger.id,
        key=ObligationKey.parse(paid.business_key),
    )
    canceled.lifecycle = ObligationLifecycle.CANCELED
    db.commit()

    response = client.get(_summary_url(ledger.id), headers=headers)

    assert response.status_code == 200
    assert response.json()["total_obligation_count"] == 1
    assert response.json()["paid_obligation_count"] == 1
    assert response.json()["paid_percentage"] == "100"
    assert response.json()["unknown_amount_count"] == 0
    assert response.json()["is_complete"] is True
    assert response.json()["amount_summaries"] == [
        {
            "currency": "PLN",
            "total_known_amount": "50.00",
            "paid_known_amount": "50.00",
            "paid_percentage": "100",
        }
    ]


def test_period_summary_for_an_empty_period_is_complete_without_percentages(
    client: TestClient, db: Session
) -> None:
    owner = create_random_user(db)
    headers = authentication_token_from_email(client=client, email=owner.email, db=db)
    ledger = ledger_use_cases.create_ledger(
        session=db, owner_user_id=owner.id, name=f"ledger-{random_lower_string()}"
    )

    response = client.get(_summary_url(ledger.id), headers=headers)

    assert response.status_code == 200
    assert response.json() == {
        "period": {"year": 2026, "month": 8},
        "total_obligation_count": 0,
        "paid_obligation_count": 0,
        "paid_percentage": None,
        "unknown_amount_count": 0,
        "is_complete": True,
        "amount_summaries": [],
    }


def test_category_history_is_continuous_and_distinguishes_missing_and_unknown(
    client: TestClient, db: Session
) -> None:
    owner = create_random_user(db)
    headers = authentication_token_from_email(client=client, email=owner.email, db=db)
    ledger = ledger_use_cases.create_ledger(
        session=db, owner_user_id=owner.id, name=f"ledger-{random_lower_string()}"
    )
    category = _create_history_category(
        db, ledger_id=ledger.id, currency=Currency.EUR
    )
    _create_history_obligation(
        db,
        ledger_id=ledger.id,
        category_code=category.code,
        period=BillingPeriod(2025, 12),
        amount=Decimal("10.00"),
    )
    _create_history_obligation(
        db,
        ledger_id=ledger.id,
        category_code=category.code,
        period=BillingPeriod(2026, 2),
        amount=None,
    )

    response = client.get(
        f"{settings.API_V1_STR}/ledgers/{ledger.id}/analytics/categories/"
        f"{category.id}/history?from=2025-12&to=2026-02",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["points"] == [
        {
            "period": {"year": 2025, "month": 12},
            "state": "known",
            "current_amount": "10.00",
            "currency": "EUR",
        },
        {
            "period": {"year": 2026, "month": 1},
            "state": "missing",
            "current_amount": None,
            "currency": "EUR",
        },
        {
            "period": {"year": 2026, "month": 2},
            "state": "unknown",
            "current_amount": None,
            "currency": "EUR",
        },
    ]


def test_category_history_preserves_each_obligations_currency(
    client: TestClient, db: Session
) -> None:
    owner = create_random_user(db)
    headers = authentication_token_from_email(client=client, email=owner.email, db=db)
    ledger = ledger_use_cases.create_ledger(
        session=db, owner_user_id=owner.id, name=f"ledger-{random_lower_string()}"
    )
    category = _create_category(db, ledger_id=ledger.id, currency=Currency.PLN)
    _create_obligation(
        db,
        ledger_id=ledger.id,
        category_code=category.code,
        period=BillingPeriod(2025, 12),
        amount=Decimal("10.00"),
    )
    category_use_cases.update_category(
        session=db,
        ledger_id=ledger.id,
        category_id=category.id,
        name=category.name,
        currency=Currency.EUR,
    )
    _create_obligation(
        db,
        ledger_id=ledger.id,
        category_code=category.code,
        period=BillingPeriod(2026, 1),
        amount=Decimal("20.00"),
    )

    response = client.get(
        f"{settings.API_V1_STR}/ledgers/{ledger.id}/analytics/categories/"
        f"{category.id}/history?from=2025-12&to=2026-01",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["points"] == [
        {
            "period": {"year": 2025, "month": 12},
            "state": "known",
            "current_amount": "10.00",
            "currency": "PLN",
        },
        {
            "period": {"year": 2026, "month": 1},
            "state": "known",
            "current_amount": "20.00",
            "currency": "EUR",
        },
    ]


def test_category_history_is_scoped_to_its_ledger_and_validates_ranges(
    client: TestClient, db: Session
) -> None:
    owner = create_random_user(db)
    headers = authentication_token_from_email(client=client, email=owner.email, db=db)
    ledger = ledger_use_cases.create_ledger(
        session=db, owner_user_id=owner.id, name=f"ledger-{random_lower_string()}"
    )
    other_ledger = ledger_use_cases.create_ledger(
        session=db, owner_user_id=owner.id, name=f"ledger-{random_lower_string()}"
    )
    category = _create_history_category(db, ledger_id=other_ledger.id)
    base_url = (
        f"{settings.API_V1_STR}/ledgers/{ledger.id}/analytics/categories/"
        f"{category.id}/history"
    )

    wrong_ledger = client.get(f"{base_url}?from=2026-01&to=2026-01", headers=headers)
    invalid_range = client.get(f"{base_url}?from=2026-02&to=2026-01", headers=headers)

    assert wrong_ledger.status_code == 404
    assert invalid_range.status_code == 422
