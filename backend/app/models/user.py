import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel

from app.models.base import get_datetime_utc


class User(SQLModel, table=True):
    email: str = Field(unique=True, index=True, max_length=255)
    is_active: bool = Field(default=True, nullable=False)
    is_superuser: bool = Field(default=False, nullable=False)
    full_name: str | None = Field(default=None, max_length=255)
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(
            DateTime(timezone=True), nullable=False, default=get_datetime_utc
        ),
    )
