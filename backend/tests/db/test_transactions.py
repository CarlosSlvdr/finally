"""Composing multiple accessors into one atomic transaction via `conn`."""

from app.db import connection, positions, profile, trades


def test_trade_executes_atomically_across_tables():
    with connection.get_connection() as conn:
        profile.adjust_cash_balance(-1500.0, conn=conn)
        positions.apply_trade("AAPL", "buy", 10, 150.0, conn=conn)
        trades.record_trade("AAPL", "buy", 10, 150.0, conn=conn)

    assert profile.get_cash_balance() == 8500.0
    pos = positions.get_position("AAPL")
    assert pos.quantity == 10
    assert len(trades.list_trades()) == 1


def test_failed_step_rolls_back_whole_transaction():
    try:
        with connection.get_connection() as conn:
            profile.adjust_cash_balance(-1500.0, conn=conn)
            positions.apply_trade("AAPL", "sell", 10, 150.0, conn=conn)  # raises: none held
    except ValueError:
        pass

    assert profile.get_cash_balance() == 10000.0
