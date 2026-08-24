import pytest
from sqlalchemy.orm import Session

from app.use_cases import categories as category_use_cases
from app.use_cases.exceptions import (
    CategoryDataValidationError,
    IncompatibleCategoryDataSchemaError,
    InvalidCategoryDataSchemaError,
)
from tests.utils.ledger_domain import create_category_tree

SCHEMA = {
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
