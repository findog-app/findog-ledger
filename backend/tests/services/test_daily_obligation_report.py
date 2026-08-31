from datetime import date
from types import SimpleNamespace

import pytest

from app.domain import BillingPeriod, ObligationLifecycle
from app.services.daily_obligation_report import _section_for


@pytest.mark.parametrize(
    ("lifecycle", "due_date", "report_date", "expected"),
    [
        (
            ObligationLifecycle.COLLECTING_DATA,
            date(2026, 9, 4),
            date(2026, 9, 1),
            "needs_preparation",
        ),
        (ObligationLifecycle.READY, date(2026, 9, 3), date(2026, 9, 1), "ready_to_pay"),
        (
            ObligationLifecycle.COLLECTING_DATA,
            date(2026, 8, 31),
            date(2026, 9, 1),
            "overdue",
        ),
        (ObligationLifecycle.PAID, date(2026, 8, 31), date(2026, 9, 1), None),
        (ObligationLifecycle.CANCELED, date(2026, 8, 31), date(2026, 9, 1), None),
    ],
)
def test_daily_report_assigns_due_obligations_to_sections(
    lifecycle: ObligationLifecycle,
    due_date: date,
    report_date: date,
    expected: str | None,
) -> None:
    obligation = SimpleNamespace(
        lifecycle=lifecycle,
        due_date=due_date,
        period_year=2026,
        period_month=9,
    )

    assert (
        _section_for(obligation, report_date, BillingPeriod.from_date(report_date))
        == expected
    )  # type: ignore[arg-type]


def test_daily_report_marks_current_period_missing_due_dates_after_the_fifth() -> None:
    obligation = SimpleNamespace(
        lifecycle=ObligationLifecycle.COLLECTING_DATA,
        due_date=None,
        period_year=2026,
        period_month=9,
    )

    assert _section_for(obligation, date(2026, 9, 4), BillingPeriod(2026, 9)) is None  # type: ignore[arg-type]
    assert (
        _section_for(obligation, date(2026, 9, 5), BillingPeriod(2026, 9))
        == "missing_due_date"
    )  # type: ignore[arg-type]
