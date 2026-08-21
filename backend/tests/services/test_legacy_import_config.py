from pathlib import Path

import pytest

from app.services.legacy_import import (
    LegacyImportConfigError,
    load_legacy_import_config,
)


def test_load_legacy_import_config_reads_dropbox_path_and_sheets(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "legacy-import.yaml"
    config_path.write_text(
        'excel_dropbox_path: "/Oplaty.xlsm"\nmonitored_sheets:\n  Home: ["C", "I"]\n',
        encoding="utf-8",
    )

    config = load_legacy_import_config(config_path)

    assert config.excel_dropbox_path == "/Oplaty.xlsm"
    assert config.monitored_sheets == {"Home": ["C", "I"]}


def test_load_legacy_import_config_rejects_missing_monitored_sheets(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "legacy-import.yaml"
    config_path.write_text('excel_dropbox_path: "/Oplaty.xlsm"\n', encoding="utf-8")

    with pytest.raises(LegacyImportConfigError):
        load_legacy_import_config(config_path)
