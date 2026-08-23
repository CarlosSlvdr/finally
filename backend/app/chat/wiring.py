"""Adapts backend-engineer's portfolio_service / app.db modules to the chat service's dep contracts."""

from __future__ import annotations

from app.db.chat import add_message, list_recent_messages
from app.db.profile import get_cash_balance
from app.db.watchlist import add_to_watchlist, list_watchlist, remove_from_watchlist
from app.market import PriceCache
from app.portfolio_service import (
    TradeValidationError,
    compute_total_value,
    execute_trade,
    positions_with_market_data,
)

from .deps import ChatHistoryEntry, PortfolioContext, PositionContext, TradeError, WatchlistContext


def build_portfolio_context(price_cache: PriceCache, user_id: str) -> PortfolioContext:
    positions = [
        PositionContext(
            ticker=p["ticker"],
            quantity=p["quantity"],
            avg_cost=p["avg_cost"],
            current_price=p["current_price"],
            unrealized_pnl=p["unrealized_pnl"],
            unrealized_pnl_percent=p["unrealized_pnl_percent"],
        )
        for p in positions_with_market_data(price_cache, user_id)
    ]
    watchlist = [
        WatchlistContext(ticker=ticker, current_price=price_cache.get_price(ticker))
        for ticker in list_watchlist(user_id)
    ]
    return PortfolioContext(
        cash_balance=get_cash_balance(user_id),
        total_value=compute_total_value(price_cache, user_id),
        positions=positions,
        watchlist=watchlist,
    )


def read_chat_history(user_id: str, limit: int) -> list[ChatHistoryEntry]:
    return [ChatHistoryEntry(role=m.role, content=m.content) for m in list_recent_messages(user_id, limit)]


def save_chat_message(user_id: str, role: str, content: str, actions: str | None) -> None:
    add_message(role, content, actions, user_id)


def make_trade_executor(price_cache: PriceCache):
    def _execute(user_id: str, ticker: str, side: str, quantity: float) -> float:
        try:
            result = execute_trade(price_cache, ticker, side, quantity, user_id)
        except TradeValidationError as exc:
            raise TradeError(str(exc)) from exc
        return result.price

    return _execute


def make_watchlist_mutator(market_source, action: str):
    async def _mutate(user_id: str, ticker: str) -> None:
        ticker = ticker.upper()
        if action == "add":
            add_to_watchlist(ticker, user_id)
            await market_source.add_ticker(ticker)
        else:
            remove_from_watchlist(ticker, user_id)
            await market_source.remove_ticker(ticker)

    return _mutate
