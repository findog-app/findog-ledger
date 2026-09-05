import json
from pathlib import Path

from scripts.export_integration_openapi import export_openapi


def test_export_openapi_uses_distinct_data_model_names(tmp_path: Path) -> None:
    output_path = tmp_path / "integration.json"

    export_openapi(output_path)

    spec = json.loads(output_path.read_text())
    schemas = spec["components"]["schemas"]

    assert spec["info"] == {
        "title": "Oblidog Integration API",
        "description": "Integration API for Oblidog Ledger.",
        "version": "1.0.0",
    }
    assert "title" not in schemas["CategoryDataRecordCreate"]["properties"]["data"]
    assert "title" not in schemas["CategoryDataRecordPublic"]["properties"]["data"]
