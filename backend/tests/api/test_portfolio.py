"""Portfolio and trade execution endpoint tests."""

from __future__ import annotations


def test_get_portfolio_initial_state(client):
    resp = client.get("/api/portfolio")
    assert resp.status_code == 200
    body = resp.json()
    assert body["cash_balance"] == 10000.0
    assert body["positions"] == []
    assert body["total_value"] == 10000.0


def test_buy_reduces_cash_and_creates_position(client):
    resp = client.post("/api/portfolio/trade", json={"ticker": "AAPL", "side": "buy", "quantity": 10})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ticker"] == "AAPL"
    assert body["cash_balance"] == 10000.0 - body["price"] * 10

    portfolio = client.get("/api/portfolio").json()
    assert len(portfolio["positions"]) == 1
    assert portfolio["positions"][0]["ticker"] == "AAPL"
    assert portfolio["positions"][0]["quantity"] == 10


def test_sell_increases_cash_and_closes_position(client):
    client.post("/api/portfolio/trade", json={"ticker": "AAPL", "side": "buy", "quantity": 5})
    resp = client.post("/api/portfolio/trade", json={"ticker": "AAPL", "side": "sell", "quantity": 5})
    assert resp.status_code == 200

    portfolio = client.get("/api/portfolio").json()
    assert portfolio["positions"] == []


def test_buy_with_insufficient_cash_fails(client):
    resp = client.post(
        "/api/portfolio/trade", json={"ticker": "NVDA", "side": "buy", "quantity": 1_000_000}
    )
    assert resp.status_code == 400
    assert "Insufficient cash" in resp.json()["detail"]

    portfolio = client.get("/api/portfolio").json()
    assert portfolio["cash_balance"] == 10000.0
    assert portfolio["positions"] == []


def test_sell_more_than_owned_fails(client):
    client.post("/api/portfolio/trade", json={"ticker": "AAPL", "side": "buy", "quantity": 2})
    resp = client.post("/api/portfolio/trade", json={"ticker": "AAPL", "side": "sell", "quantity": 5})
    assert resp.status_code == 400
    assert "Insufficient shares" in resp.json()["detail"]

    portfolio = client.get("/api/portfolio").json()
    assert portfolio["positions"][0]["quantity"] == 2


def test_sell_without_position_fails(client):
    resp = client.post("/api/portfolio/trade", json={"ticker": "TSLA", "side": "sell", "quantity": 1})
    assert resp.status_code == 400
    assert "Insufficient shares" in resp.json()["detail"]


def test_sell_at_a_loss_still_settles_cash_correctly(client):
    buy = client.post(
        "/api/portfolio/trade", json={"ticker": "AAPL", "side": "buy", "quantity": 10}
    ).json()
    cash_after_buy = buy["cash_balance"]

    sell = client.post(
        "/api/portfolio/trade", json={"ticker": "AAPL", "side": "sell", "quantity": 10}
    ).json()

    # Cash after sell reflects proceeds at the (possibly lower) sell price,
    # regardless of the original cost basis -- no realized-loss floor.
    assert sell["cash_balance"] == cash_after_buy + sell["price"] * 10


def test_invalid_side_rejected(client):
    resp = client.post("/api/portfolio/trade", json={"ticker": "AAPL", "side": "hold", "quantity": 1})
    assert resp.status_code == 422


def test_trade_history_records_snapshot(client):
    client.post("/api/portfolio/trade", json={"ticker": "AAPL", "side": "buy", "quantity": 1})
    resp = client.get("/api/portfolio/history")
    assert resp.status_code == 200
    snapshots = resp.json()
    assert len(snapshots) >= 1
    assert "total_value" in snapshots[0]
