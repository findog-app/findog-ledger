from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.routing import APIRoute

from app.api.routes.integration import router as integration_router
from app.core.config import settings


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


def build_integration_app() -> FastAPI:
    app = FastAPI(
        title="Findog Integration API",
        version="1.0.0",
        generate_unique_id_function=custom_generate_unique_id,
    )
    app.include_router(integration_router, prefix=settings.API_V1_STR)
    return app


def export_openapi(output_path: Path) -> None:
    app = build_integration_app()
    spec = app.openapi()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(spec, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    output_path = repo_root / "openapi" / "integration.json"
    export_openapi(output_path)
    print(f"Exported integration OpenAPI schema to {output_path}")


if __name__ == "__main__":
    main()
