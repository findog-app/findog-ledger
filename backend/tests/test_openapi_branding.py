from app.core.config import settings
from app.main import app


def test_full_openapi_uses_project_name_and_oblidog_description() -> None:
    spec = app.openapi()

    assert spec["info"]["title"] == settings.PROJECT_NAME
    assert spec["info"]["description"] == "API for Oblidog Ledger."
