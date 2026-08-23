import pytest

from app.db import positions


def test_get_position_unknown_returns_none():
    assert positions.get_position("AAPL") is None


def test_buy_opens_new_position():
    pos = positions.apply_trade("AAPL", "buy", 10, 100.0)
    assert pos.ticker == "AAPL"
    assert pos.quantity == 10
    assert pos.avg_cost == 100.0


def test_buy_more_weights_average_cost():
    positions.apply_trade("AAPL", "buy", 10, 100.0)
    pos = positions.apply_trade("AAPL", "buy", 10, 200.0)
    assert pos.quantity == 20
    assert pos.avg_cost == 150.0


def test_sell_partial_reduces_quantity_keeps_avg_cost():
    positions.apply_trade("AAPL", "buy", 10, 100.0)
    pos = positions.apply_trade("AAPL", "sell", 4, 150.0)
    assert pos.quantity == 6
    assert pos.avg_cost == 100.0


def test_sell_all_closes_position():
    positions.apply_trade("AAPL", "buy", 10, 100.0)
    result = positions.apply_trade("AAPL", "sell", 10, 150.0)
    assert result is None
    assert positions.get_position("AAPL") is None


def test_sell_more_than_held_raises():
    positions.apply_trade("AAPL", "buy", 5, 100.0)
    with pytest.raises(ValueError):
        positions.apply_trade("AAPL", "sell", 10, 100.0)


def test_sell_with_no_position_raises():
    with pytest.raises(ValueError):
        positions.apply_trade("AAPL", "sell", 1, 100.0)


def test_invalid_side_raises():
    with pytest.raises(ValueError):
        positions.apply_trade("AAPL", "short", 1, 100.0)


def test_nonpositive_quantity_raises():
    with pytest.raises(ValueError):
        positions.apply_trade("AAPL", "buy", 0, 100.0)


def test_list_positions_ordered_by_ticker():
    positions.apply_trade("TSLA", "buy", 1, 200.0)
    positions.apply_trade("AAPL", "buy", 1, 100.0)
    tickers = [p.ticker for p in positions.list_positions()]
    assert tickers == ["AAPL", "TSLA"]
