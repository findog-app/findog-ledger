from datetime import date
from types import SimpleNamespace

import pytest

from app.domain import BillingPeriod, ObligationLifecycle
from app.domain.business_calendar import BusinessCalendar
from app.services.daily_obligation_report import _section_for

CALENDAR = BusinessCalendar("PL")


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
        _section_for(
            obligation, report_date, BillingPeriod.from_date(report_date), CALENDAR
        )
        == expected
    )  # type: ignore[arg-type]


def test_daily_report_marks_current_period_missing_due_dates_from_fifth_business_day() -> (
    None
):
    obligation = SimpleNamespace(
        lifecycle=ObligationLifecycle.COLLECTING_DATA,
        due_date=None,
        period_year=2026,
        period_month=9,
    )

    assert (
        _section_for(obligation, date(2026, 9, 4), BillingPeriod(2026, 9), CALENDAR)
        is None
    )  # type: ignore[arg-type]
    assert (
        _section_for(obligation, date(2026, 9, 7), BillingPeriod(2026, 9), CALENDAR)
        == "missing_due_date"
    )  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("lifecycle", "due_date", "expected"),
    [
        (ObligationLifecycle.READY, date(2026, 6, 8), "ready_to_pay"),
        (ObligationLifecycle.READY, date(2026, 6, 9), None),
        (ObligationLifecycle.COLLECTING_DATA, date(2026, 6, 9), "needs_preparation"),
        (ObligationLifecycle.COLLECTING_DATA, date(2026, 6, 10), None),
    ],
)
def test_daily_report_counts_weekends_and_polish_holidays_as_non_business_days(
    lifecycle: ObligationLifecycle, due_date: date, expected: str | None
) -> None:
    # 2026-06-04 (Corpus Christi) and the following weekend do not consume lead time.
    obligation = SimpleNamespace(
        lifecycle=lifecycle,
        due_date=due_date,
        period_year=2026,
        period_month=6,
    )

    assert (
        _section_for(obligation, date(2026, 6, 3), BillingPeriod(2026, 6), CALENDAR)
        == expected
    )  # type: ignore[arg-type]


def test_daily_report_uses_fifth_business_day_for_missing_due_dates() -> None:
    obligation = SimpleNamespace(
        lifecycle=ObligationLifecycle.COLLECTING_DATA,
        due_date=None,
        period_year=2026,
        period_month=1,
    )

    # New Year's Day and Epiphany are Polish public holidays; 2026-01-09 is day five.
    assert (
        _section_for(obligation, date(2026, 1, 8), BillingPeriod(2026, 1), CALENDAR)
        is None
    )  # type: ignore[arg-type]
    assert (
        _section_for(obligation, date(2026, 1, 9), BillingPeriod(2026, 1), CALENDAR)
        == "missing_due_date"
    )  # type: ignore[arg-type]


@pytest.mark.parametrize("due_date", [date(2026, 5, 1), date(2026, 12, 31), None])
def test_daily_report_always_reports_errors_in_the_dedicated_section(
    due_date: date | None,
) -> None:
    obligation = SimpleNamespace(
        lifecycle=ObligationLifecycle.ERROR,
        due_date=due_date,
        period_year=2025,
        period_month=1,
    )

    assert (
        _section_for(obligation, date(2026, 6, 3), BillingPeriod(2026, 6), CALENDAR)
        == "errors"
    )  # type: ignore[arg-type]
