from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_watchlist_and_mock_market_api(tmp_path) -> None:
    settings = Settings(app_env="test", database_url=f"sqlite:///{tmp_path / 'market.db'}")
    payload = {
        "name": "Pilot",
        "instruments": [
            {
                "symbol": "AAPL",
                "exchange": "NASDAQ",
                "name": "Apple Inc.",
                "asset_type": "STOCK",
            }
        ],
    }
    with TestClient(create_app(settings)) as client:
        created = client.post("/api/v1/watchlists", json=payload)
        market = client.get("/api/v1/market/AAPL?provider=mock&limit=3")
        refreshed = client.post(
            "/api/v1/market/refresh",
            json={"symbols": ["AAPL"], "provider": "mock", "limit": 3},
        )
        analysis = client.get(
            "/api/v1/analysis/AAPL/technical?provider=mock&refresh=true&limit=100"
        )
        instruments = client.get("/api/v1/instruments")

    assert created.status_code == 201
    assert created.json()["instruments"][0]["symbol"] == "AAPL"
    assert instruments.status_code == 200
    assert market.status_code == 200
    assert market.json()["provider"] == "mock"
    assert len(market.json()["bars"]) == 3
    assert refreshed.status_code == 200
    assert refreshed.json()["bars_stored"] == 0
    assert analysis.status_code == 200
    assert analysis.json()["data_points"] == 100
    assert analysis.json()["technical_score"] >= 0
    assert analysis.json()["indicators"]["sma_20"] is not None
