"""Watchlist endpoint tests."""

from __future__ import annotations


def test_get_watchlist_returns_default_tickers(client):
    resp = client.get("/api/watchlist")
    assert resp.status_code == 200
    tickers = {row["ticker"] for row in resp.json()}
    assert "AAPL" in tickers
    assert len(tickers) == 10


def test_add_and_remove_ticker(client):
    resp = client.post("/api/watchlist", json={"ticker": "pypl"})
    assert resp.status_code == 200
    assert resp.json() == {"ticker": "PYPL"}

    tickers = {row["ticker"] for row in client.get("/api/watchlist").json()}
    assert "PYPL" in tickers

    resp = client.delete("/api/watchlist/PYPL")
    assert resp.status_code == 200

    tickers = {row["ticker"] for row in client.get("/api/watchlist").json()}
    assert "PYPL" not in tickers


def test_remove_unknown_ticker_404(client):
    resp = client.delete("/api/watchlist/ZZZZ")
    assert resp.status_code == 404
