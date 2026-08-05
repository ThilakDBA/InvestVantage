from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_health_reports_safe_paper_mode(tmp_path) -> None:
    settings = Settings(
        app_env="test",
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
    )

    with TestClient(create_app(settings)) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "InvestVantage",
        "environment": "test",
        "database": "ok",
        "trading_mode": "paper",
    }


def test_data_health_reports_inventory_and_keeps_broker_disabled(tmp_path) -> None:
    settings = Settings(
        app_env="test",
        database_url=f"sqlite:///{tmp_path / 'data-health.db'}",
    )

    with TestClient(create_app(settings)) as client:
        response = client.get("/api/v1/system/data-health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["active_instruments"] == 0
    assert payload["price_inventory"] == []
    assert payload["research_inventory"] == []
    assert payload["broker_orders_enabled"] is False
    assert payload["providers"][0] == {
        "name": "mock",
        "configured": True,
        "classification": "synthetic",
    }
