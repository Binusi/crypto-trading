from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_assets_returns_default_universe():
    r = client.get("/assets")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    symbols = {a["symbol"] for a in data}
    assert {"BTC", "ETH"}.issubset(symbols)


def test_simulate_without_model_returns_503(tmp_path, monkeypatch):
    from app.core.config import settings as s
    monkeypatch.setattr(s, "model_path", tmp_path / "missing.pkl")
    r = client.post(
        "/simulate",
        json={"start_date": "2023-01-01", "end_date": "2023-02-01", "starting_capital": 1000},
    )
    assert r.status_code == 503
