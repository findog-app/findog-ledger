from datetime import date

from app.domain.business_calendar import BusinessCalendar


def test_business_days_until_skips_weekends_and_polish_public_holidays() -> None:
    calendar = BusinessCalendar("PL")

    # 2026-01-01 is New Year's Day, followed by a weekend.
    assert (
        calendar.business_days_until(start=date(2025, 12, 31), end=date(2026, 1, 5))
        == 2
    )


def test_nth_business_day_of_month_handles_year_boundary() -> None:
    calendar = BusinessCalendar("PL")

    assert calendar.nth_business_day_of_month(year=2026, month=1, n=5) == date(
        2026, 1, 9
    )
