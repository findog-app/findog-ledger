import threading
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category, CategoryData
from app.use_cases import categories as category_use_cases
from app.use_cases.exceptions import (
    CategoryDataValidationError,
    IncompatibleCategoryDataSchemaError,
    InvalidCategoryDataSchemaError,
)
from tests.utils.ledger_domain import create_category_tree

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "invoice_available": {"type": "boolean"},
        "meter_reading_kwh": {"type": "number"},
    },
    "required": ["invoice_available"],
    "additionalProperties": False,
}


def test_category_data_is_validated_and_returns_active_schema_metadata(
    db: Session,
) -> None:
    ledger, _, category = create_category_tree(db)
    schema = category_use_cases.set_category_data_schema(
        session=db, ledger_id=ledger.id, category_id=category.id, schema=SCHEMA
    )

    category_data = category_use_cases.update_category_data(
        session=db,
        ledger_id=ledger.id,
        category_id=category.id,
        data={"invoice_available": True, "meter_reading_kwh": 12345.6},
    )

    assert schema.version == 1
    assert category_data.schema_version == schema.version
    assert category_data.data["invoice_available"] is True
    assert (
        category_use_cases.get_category_data_schema(
            session=db, ledger_id=ledger.id, category_id=category.id
        ).id
        == schema.id
    )


def test_category_data_rejects_unknown_fields_and_invalid_values(db: Session) -> None:
    ledger, _, category = create_category_tree(db)
    category_use_cases.set_category_data_schema(
        session=db, ledger_id=ledger.id, category_id=category.id, schema=SCHEMA
    )

    with pytest.raises(CategoryDataValidationError, match="Additional properties"):
        category_use_cases.update_category_data(
            session=db,
            ledger_id=ledger.id,
            category_id=category.id,
            data={"invoice_available": True, "unexpected": "value"},
        )


def test_category_data_enforces_date_format(db: Session) -> None:
    ledger, _, category = create_category_tree(db)
    category_use_cases.set_category_data_schema(
        session=db,
        ledger_id=ledger.id,
        category_id=category.id,
        schema={
            "type": "object",
            "properties": {"reading_date": {"type": "string", "format": "date"}},
            "required": ["reading_date"],
        },
    )

    saved_data = category_use_cases.update_category_data(
        session=db,
        ledger_id=ledger.id,
        category_id=category.id,
        data={"reading_date": "2026-08-24"},
    )
    assert saved_data.data == {"reading_date": "2026-08-24"}

    with pytest.raises(CategoryDataValidationError, match="is not a 'date'"):
        category_use_cases.update_category_data(
            session=db,
            ledger_id=ledger.id,
            category_id=category.id,
            data={"reading_date": "2026-02-30"},
        )


def test_new_schema_versions_are_immutable_and_compatible_with_saved_data(
    db: Session,
) -> None:
    ledger, _, category = create_category_tree(db)
    original = category_use_cases.set_category_data_schema(
        session=db, ledger_id=ledger.id, category_id=category.id, schema=SCHEMA
    )
    category_use_cases.update_category_data(
        session=db,
        ledger_id=ledger.id,
        category_id=category.id,
        data={"invoice_available": True},
    )
    next_schema = category_use_cases.set_category_data_schema(
        session=db,
        ledger_id=ledger.id,
        category_id=category.id,
        schema={
            **SCHEMA,
            "properties": {**SCHEMA["properties"], "note": {"type": "string"}},
        },
    )

    assert original.version == 1
    assert original.is_active is False
    assert next_schema.version == 2
    assert next_schema.is_active is True
    assert original.schema == SCHEMA
    assert (
        category_use_cases.get_category_data(
            session=db, ledger_id=ledger.id, category_id=category.id
        ).schema_version
        == next_schema.version
    )


def test_incompatible_schema_and_invalid_json_schema_are_rejected(db: Session) -> None:
    ledger, _, category = create_category_tree(db)
    category_use_cases.set_category_data_schema(
        session=db, ledger_id=ledger.id, category_id=category.id, schema=SCHEMA
    )
    category_use_cases.update_category_data(
        session=db,
        ledger_id=ledger.id,
        category_id=category.id,
        data={"invoice_available": True},
    )

    with pytest.raises(IncompatibleCategoryDataSchemaError):
        category_use_cases.set_category_data_schema(
            session=db,
            ledger_id=ledger.id,
            category_id=category.id,
            schema={"type": "object", "required": ["must_be_present"]},
        )
    with pytest.raises(InvalidCategoryDataSchemaError):
        category_use_cases.set_category_data_schema(
            session=db,
            ledger_id=ledger.id,
            category_id=category.id,
            schema={"type": "not-a-json-schema-type"},
        )
    with pytest.raises(
        InvalidCategoryDataSchemaError, match="root type must be object"
    ):
        category_use_cases.set_category_data_schema(
            session=db,
            ledger_id=ledger.id,
            category_id=category.id,
            schema={"type": "string"},
        )


def test_category_data_patch_serializes_concurrent_updates(db: Session) -> None:
    ledger, _, category = create_category_tree(db)
    category_use_cases.set_category_data_schema(
        session=db, ledger_id=ledger.id, category_id=category.id, schema=SCHEMA
    )
    category_use_cases.update_category_data(
        session=db,
        ledger_id=ledger.id,
        category_id=category.id,
        data={"invoice_available": True, "meter_reading_kwh": 1.0},
    )

    lock_session = Session(bind=db.get_bind())
    lock_session.scalar(
        select(Category).where(Category.id == category.id).with_for_update()
    )
    patch_started = threading.Event()
    patch_finished = threading.Event()

    def apply_patch() -> None:
        patch_started.set()
        with Session(bind=db.get_bind()) as patch_session:
            category_use_cases.patch_category_data(
                session=patch_session,
                ledger_id=ledger.id,
                category_id=category.id,
                patch={"meter_reading_kwh": 2.0},
            )
        patch_finished.set()

    patch_thread = threading.Thread(target=apply_patch)
    patch_thread.start()
    assert patch_started.wait(timeout=1)
    assert not patch_finished.wait(timeout=0.2)

    locked_data = lock_session.get(CategoryData, category.id)
    assert locked_data is not None
    locked_data.data = {"invoice_available": False, "meter_reading_kwh": 1.0}
    lock_session.commit()
    patch_thread.join(timeout=5)
    assert patch_finished.is_set()

    db.expire_all()
    category_data = category_use_cases.get_category_data(
        session=db, ledger_id=ledger.id, category_id=category.id
    )
    assert category_data.data == {
        "invoice_available": False,
        "meter_reading_kwh": 2.0,
    }
