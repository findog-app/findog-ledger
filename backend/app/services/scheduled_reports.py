"""Reusable, HTTP-independent scheduled report delivery."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.report_delivery import ReportDeliveryStatus
from app.models import ReportDelivery, User
from app.utils import EmailData, send_email

if TYPE_CHECKING:
    from app.use_cases.system_runs import SystemRunContext


class ScheduledReport(Protocol):
    report_type: str

    def recipients(
        self, *, session: Session, context: SystemRunContext
    ) -> Sequence[User]: ...

    def delivery_key(self, *, user: User, context: SystemRunContext) -> str: ...

    def render(self, *, user: User, context: SystemRunContext) -> EmailData: ...


@dataclass(frozen=True, slots=True)
class DeliverySummary:
    sent: int = 0
    skipped: int = 0
    failed: int = 0


def deliver_scheduled_report(
    *, session: Session, report: ScheduledReport, context: SystemRunContext
) -> DeliverySummary:
    sent = skipped = failed = 0
    for user in report.recipients(session=session, context=context):
        if not user.email:
            continue
        delivery_key = report.delivery_key(user=user, context=context)
        delivery = session.scalar(
            select(ReportDelivery).where(
                ReportDelivery.user_id == user.id,
                ReportDelivery.delivery_key == delivery_key,
            )
        )
        if delivery is not None and delivery.status is ReportDeliveryStatus.SENT:
            skipped += 1
            continue
        if delivery is None:
            delivery = ReportDelivery(
                report_type=report.report_type,
                user_id=user.id,
                delivery_key=delivery_key,
                status=ReportDeliveryStatus.FAILED,
            )
            session.add(delivery)
        else:
            delivery.report_type = report.report_type
            delivery.error_message = None
        session.commit()
        try:
            email = report.render(user=user, context=context)
            send_email(
                email_to=user.email,
                subject=email.subject,
                html_content=email.html_content,
            )
        except Exception as exc:
            session.rollback()
            delivery = session.get(ReportDelivery, delivery.id)
            if delivery is not None:
                delivery.status = ReportDeliveryStatus.FAILED
                delivery.error_message = _safe_error(exc)
                session.commit()
            failed += 1
        else:
            delivery = session.get(ReportDelivery, delivery.id)
            if delivery is not None:
                delivery.status = ReportDeliveryStatus.SENT
                delivery.sent_at = datetime.now(UTC)
                delivery.error_message = None
                session.commit()
            sent += 1
    return DeliverySummary(sent=sent, skipped=skipped, failed=failed)


def _safe_error(exc: Exception) -> str:
    return " ".join(str(exc).split())[:1000] or exc.__class__.__name__
