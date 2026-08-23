from app.chat.mock import mock_llm_response


def test_buy_pattern_creates_trade():
    resp = mock_llm_response("please buy 5 AAPL for me")
    assert [t.model_dump() for t in resp.trades] == [{"ticker": "AAPL", "side": "buy", "quantity": 5.0}]
    assert resp.watchlist_changes is None


def test_sell_pattern_is_case_insensitive():
    resp = mock_llm_response("SELL 2.5 tsla now")
    assert resp.trades[0].ticker == "TSLA"
    assert resp.trades[0].side == "sell"
    assert resp.trades[0].quantity == 2.5


def test_multiple_trades_in_one_message():
    resp = mock_llm_response("buy 1 AAPL and sell 3 MSFT")
    assert len(resp.trades) == 2


def test_watch_and_add_patterns():
    resp = mock_llm_response("watch NVDA")
    assert [c.model_dump() for c in resp.watchlist_changes] == [{"ticker": "NVDA", "action": "add"}]

    resp2 = mock_llm_response("add PYPL to my list")
    assert [c.model_dump() for c in resp2.watchlist_changes] == [{"ticker": "PYPL", "action": "add"}]


def test_unwatch_and_remove_patterns():
    resp = mock_llm_response("unwatch NVDA")
    assert [c.model_dump() for c in resp.watchlist_changes] == [{"ticker": "NVDA", "action": "remove"}]

    resp2 = mock_llm_response("remove PYPL")
    assert [c.model_dump() for c in resp2.watchlist_changes] == [{"ticker": "PYPL", "action": "remove"}]


def test_no_pattern_matches_gives_plain_message():
    resp = mock_llm_response("what do you think about the market today?")
    assert resp.trades is None
    assert resp.watchlist_changes is None
    assert resp.message
