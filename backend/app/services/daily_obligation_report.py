"""Conditional daily obligation digest."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.domain import BillingPeriod, ObligationLifecycle, ValueState
from app.models import Ledger, LedgerMembership, Obligation, User
from app.utils import EmailData, render_email_template

if TYPE_CHECKING:
    from app.use_cases.system_runs import SystemRunContext

PREPARATION_DAYS = 3
READY_TO_PAY_DAYS = 2
MISSING_DUE_DATE_DAY = 5


@dataclass(frozen=True, slots=True)
class DailyReportItem:
    ledger_name: str
    category_name: str
    due_date: date | None
    amount: Decimal | None
    currency: str | None
    amount_state: ValueState
    due_date_state: ValueState
    link: str


class DailyObligationReport:
    report_type = "daily_obligations"

    def recipients(self, *, session: Session, context: SystemRunContext) -> list[User]:
        return list(
            session.scalars(
                select(User)
                .join(LedgerMembership, LedgerMembership.user_id == User.id)
                .join(Ledger, Ledger.id == LedgerMembership.ledger_id)
                .where(User.is_active, Ledger.is_active)
                .distinct()
                .order_by(User.id)
            )
        )

    def delivery_key(self, *, user: User, context: SystemRunContext) -> str:
        return f"daily:{user.id}:{context.business_date.isoformat()}"

    def render(
        self, *, session: Session, user: User, context: SystemRunContext
    ) -> EmailData | None:
        sections = _select_sections(
            session=session, user=user, report_date=context.business_date
        )
        if not any(sections.values()):
            return None
        rendered = {
            name: _group_by_ledger(items) for name, items in sections.items() if items
        }
        template_context = {
            "project_name": settings.PROJECT_NAME,
            "report_date": context.business_date.isoformat(),
            "sections": rendered,
        }
        return EmailData(
            subject=f"{settings.PROJECT_NAME} - Daily obligation report",
            html_content=render_email_template(
                template_name="daily_obligation_report.html", context=template_context
            ),
            text_content=render_email_template(
                template_name="daily_obligation_report.txt", context=template_context
            ),
        )


def _select_sections(
    *, session: Session, user: User, report_date: date
) -> dict[str, list[DailyReportItem]]:
    period = BillingPeriod.from_date(report_date)
    obligations = session.scalars(
        select(Obligation)
        .join(LedgerMembership, LedgerMembership.ledger_id == Obligation.ledger_id)
        .join(Ledger, Ledger.id == Obligation.ledger_id)
        .where(LedgerMembership.user_id == user.id, Ledger.is_active)
        .options(joinedload(Obligation.ledger), joinedload(Obligation.category))
    ).unique()
    sections: dict[str, list[DailyReportItem]] = defaultdict(list)
    for obligation in obligations:
        section = _section_for(obligation, report_date, period)
        if section is not None:
            sections[section].append(_item(obligation))
    return sections


def _section_for(
    obligation: Obligation, report_date: date, period: BillingPeriod
) -> str | None:
    if obligation.lifecycle in {ObligationLifecycle.PAID, ObligationLifecycle.CANCELED}:
        return None
    if obligation.due_date is not None and obligation.due_date < report_date:
        return "overdue"
    if obligation.lifecycle is ObligationLifecycle.READY:
        if (
            obligation.due_date is not None
            and (obligation.due_date - report_date).days <= READY_TO_PAY_DAYS
        ):
            return "ready_to_pay"
        return None
    if obligation.due_date is None:
        if (obligation.period_year, obligation.period_month) == (
            period.year,
            period.month,
        ) and report_date.day >= MISSING_DUE_DATE_DAY:
            return "missing_due_date"
        return None
    if (obligation.due_date - report_date).days <= PREPARATION_DAYS:
        return "needs_preparation"
    return None


def _item(obligation: Obligation) -> DailyReportItem:
    return DailyReportItem(
        ledger_name=obligation.ledger.name,
        category_name=obligation.category.name,
        due_date=obligation.due_date,
        amount=obligation.current_amount,
        currency=obligation.currency,
        amount_state=obligation.amount_state,
        due_date_state=obligation.due_date_state,
        link=f"{settings.FRONTEND_HOST}/ledgers/{obligation.ledger_id}/obligations/{obligation.id}",
    )


def _group_by_ledger(items: list[DailyReportItem]) -> dict[str, list[DailyReportItem]]:
    grouped: dict[str, list[DailyReportItem]] = defaultdict(list)
    for item in items:
        grouped[item.ledger_name].append(item)
    return dict(grouped)
