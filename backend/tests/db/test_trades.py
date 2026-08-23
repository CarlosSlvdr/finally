from app.db import trades


def test_record_trade_returns_trade():
    t = trades.record_trade("AAPL", "buy", 10, 150.0)
    assert t.ticker == "AAPL"
    assert t.side == "buy"
    assert t.quantity == 10
    assert t.price == 150.0


def test_list_trades_newest_first():
    trades.record_trade("AAPL", "buy", 1, 100.0)
    trades.record_trade("GOOGL", "buy", 1, 200.0)
    result = trades.list_trades()
    assert [t.ticker for t in result] == ["GOOGL", "AAPL"]


def test_list_trades_respects_limit():
    for i in range(5):
        trades.record_trade("AAPL", "buy", 1, 100.0 + i)
    assert len(trades.list_trades(limit=2)) == 2
