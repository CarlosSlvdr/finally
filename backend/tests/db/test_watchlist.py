from app.db import watchlist
from app.db.seed import DEFAULT_TICKERS


def test_list_watchlist_returns_seeded_defaults():
    tickers = watchlist.list_watchlist()
    assert set(tickers) == set(DEFAULT_TICKERS)
    assert len(tickers) == 10


def test_add_to_watchlist():
    watchlist.add_to_watchlist("pypl")
    assert "PYPL" in watchlist.list_watchlist()


def test_add_to_watchlist_is_idempotent():
    watchlist.add_to_watchlist("AAPL")
    watchlist.add_to_watchlist("AAPL")
    assert watchlist.list_watchlist().count("AAPL") == 1


def test_remove_from_watchlist():
    watchlist.remove_from_watchlist("AAPL")
    assert "AAPL" not in watchlist.list_watchlist()


def test_remove_unknown_ticker_is_noop():
    watchlist.remove_from_watchlist("NOPE")
    assert len(watchlist.list_watchlist()) == 10
