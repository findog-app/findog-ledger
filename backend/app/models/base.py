from datetime import UTC, datetime

from sqlalchemy.orm import DeclarativeBase


def get_datetime_utc() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass
