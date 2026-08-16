from datetime import datetime, timezone

from sqlalchemy.orm import DeclarativeBase


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass
