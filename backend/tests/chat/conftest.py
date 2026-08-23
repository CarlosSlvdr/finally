"""Fake dependency implementations for chat service tests."""

from __future__ import annotations

import pytest

from app.chat.deps import (
    ChatHistoryEntry,
    PortfolioContext,
    PositionContext,
    TradeError,
    WatchlistContext,
)


class FakeDeps:
    def __init__(self) -> None:
        self.cash_balance = 10_000.0
        self.positions: dict[str, PositionContext] = {}
        self.watchlist: dict[str, WatchlistContext] = {
            "AAPL": WatchlistContext(ticker="AAPL", current_price=190.0),
        }
        self.history: list[ChatHistoryEntry] = []
        self.saved_messages: list[tuple[str, str, str, str | None]] = []
        self.fail_trade_error: str | None = None
        self.fail_watchlist_error: str | None = None

    def get_portfolio_context(self, user_id: str) -> PortfolioContext:
        total = self.cash_balance + sum(
            p.quantity * p.current_price for p in self.positions.values()
        )
        return PortfolioContext(
            cash_balance=self.cash_balance,
            total_value=total,
            positions=list(self.positions.values()),
            watchlist=list(self.watchlist.values()),
        )

    def get_history(self, user_id: str, limit: int) -> list[ChatHistoryEntry]:
        return self.history[-limit:]

    def save_message(self, user_id: str, role: str, content: str, actions: str | None) -> None:
        self.saved_messages.append((user_id, role, content, actions))

    def execute_trade(self, user_id: str, ticker: str, side: str, quantity: float) -> float:
        if self.fail_trade_error:
            raise TradeError(self.fail_trade_error)
        price = self.watchlist.get(ticker, WatchlistContext(ticker=ticker, current_price=100.0)).current_price or 100.0
        if side == "buy":
            self.cash_balance -= price * quantity
        else:
            self.cash_balance += price * quantity
        self.positions[ticker] = PositionContext(
            ticker=ticker,
            quantity=quantity,
            avg_cost=price,
            current_price=price,
            unrealized_pnl=0.0,
            unrealized_pnl_percent=0.0,
        )
        return price

    async def add_watchlist_ticker(self, user_id: str, ticker: str) -> None:
        if self.fail_watchlist_error:
            raise TradeError(self.fail_watchlist_error)
        self.watchlist[ticker] = WatchlistContext(ticker=ticker, current_price=None)

    async def remove_watchlist_ticker(self, user_id: str, ticker: str) -> None:
        if self.fail_watchlist_error:
            raise TradeError(self.fail_watchlist_error)
        self.watchlist.pop(ticker, None)

    def kwargs(self) -> dict:
        return {
            "get_portfolio_context": self.get_portfolio_context,
            "get_history": self.get_history,
            "save_message": self.save_message,
            "execute_trade": self.execute_trade,
            "add_watchlist_ticker": self.add_watchlist_ticker,
            "remove_watchlist_ticker": self.remove_watchlist_ticker,
        }


@pytest.fixture
def fake_deps() -> FakeDeps:
    return FakeDeps()
