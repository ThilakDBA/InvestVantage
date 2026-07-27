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
