from app.chat.deps import ChatHistoryEntry, PortfolioContext, PositionContext, WatchlistContext
from app.chat.prompt import build_messages, format_portfolio_context


def test_format_portfolio_context_includes_positions_and_watchlist():
    ctx = PortfolioContext(
        cash_balance=5000.0,
        total_value=7000.0,
        positions=[
            PositionContext(
                ticker="AAPL",
                quantity=10,
                avg_cost=180.0,
                current_price=200.0,
                unrealized_pnl=200.0,
                unrealized_pnl_percent=11.11,
            )
        ],
        watchlist=[WatchlistContext(ticker="TSLA", current_price=250.0)],
    )
    text = format_portfolio_context(ctx)
    assert "AAPL" in text
    assert "$5,000.00" in text
    assert "TSLA" in text


def test_format_portfolio_context_handles_empty_state():
    ctx = PortfolioContext(cash_balance=10000.0, total_value=10000.0, positions=[], watchlist=[])
    text = format_portfolio_context(ctx)
    assert "Positions: none" in text
    assert "Watchlist: empty" in text


def test_build_messages_includes_system_history_and_user_message():
    ctx = PortfolioContext(cash_balance=10000.0, total_value=10000.0, positions=[], watchlist=[])
    history = [ChatHistoryEntry(role="user", content="hi"), ChatHistoryEntry(role="assistant", content="hello")]
    messages = build_messages(ctx, history, "buy 5 AAPL")

    assert messages[0]["role"] == "system"
    assert messages[1] == {"role": "user", "content": "hi"}
    assert messages[2] == {"role": "assistant", "content": "hello"}
    assert messages[-1] == {"role": "user", "content": "buy 5 AAPL"}
