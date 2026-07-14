import pytest


@pytest.mark.asyncio
async def test_health_endpoint_reports_database_and_pool_settings(client) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database_status"] == "ok"
    assert body["database_pool"]["pool_size"] == 10
    assert body["database_pool"]["max_overflow"] == 20
    assert body["database_pool"]["pool_recycle_seconds"] == 1800
    assert body["database_pool"]["pool_pre_ping"] is True
