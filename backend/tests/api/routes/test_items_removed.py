from fastapi.testclient import TestClient

from app.core.config import settings


def test_items_collection_endpoint_removed(client: TestClient) -> None:
    response = client.get(f"{settings.API_V1_STR}/items/")

    assert response.status_code == 404


def test_items_detail_endpoint_removed(client: TestClient) -> None:
    response = client.get(f"{settings.API_V1_STR}/items/test-id")

    assert response.status_code == 404
