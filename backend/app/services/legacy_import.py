from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator


class LegacyImportConfigError(ValueError):
    pass


class LegacyImportConfig(BaseModel):
    excel_dropbox_path: str = Field(min_length=1)
    monitored_sheets: dict[str, list[str]]

    @field_validator("monitored_sheets")
    @classmethod
    def validate_monitored_sheets(
        cls, value: dict[str, list[str]]
    ) -> dict[str, list[str]]:
        if not value:
            raise ValueError("must not be empty")
        for sheet_name, columns in value.items():
            if (
                not sheet_name.strip()
                or not columns
                or any(not column.strip() for column in columns)
            ):
                raise ValueError(
                    "must map non-empty sheet names to non-empty column lists"
                )
        return value


def load_legacy_import_config(path: Path) -> LegacyImportConfig:
    try:
        with path.open(encoding="utf-8") as config_file:
            raw_config = yaml.safe_load(config_file)
    except OSError as exc:
        raise LegacyImportConfigError(
            f"Legacy import configuration cannot be read from {path}"
        ) from exc
    except yaml.YAMLError as exc:
        raise LegacyImportConfigError(
            "Legacy import configuration is not valid YAML"
        ) from exc

    try:
        return LegacyImportConfig.model_validate(raw_config)
    except ValidationError as exc:
        raise LegacyImportConfigError("Legacy import configuration is invalid") from exc
