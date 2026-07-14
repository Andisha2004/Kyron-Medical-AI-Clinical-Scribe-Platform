from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_returns_successful_response() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "Kyron Medical Clinical Assistant API"
    assert body["environment"] == "development"
