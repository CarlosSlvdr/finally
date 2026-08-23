"""Trade execution and portfolio valuation logic.

Reused by the REST API and (via execute_trade) by the LLM chat flow.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from app.db.connection import get_connection
from app.db.positions import apply_trade, get_position, list_positions
from app.db.profile import adjust_cash_balance, get_cash_balance
from app.db.snapshots import record_snapshot
from app.db.trades import record_trade
from app.market import PriceCache


class TradeValidationError(Exception):
    """Raised when a trade cannot be executed (insufficient cash or shares)."""


@dataclass(frozen=True, slots=True)
class TradeResult:
    ticker: str
    side: str
    quantity: float
    price: float
    cash_balance: float


def execute_trade(
    price_cache: PriceCache,
    ticker: str,
    side: str,
    quantity: float,
    user_id: str = "default",
) -> TradeResult:
    """Execute a market order at the current cached price.

    Validates sufficient cash (buy) or sufficient shares (sell), then updates
    the position, cash balance, trade log, and a portfolio snapshot atomically
    in one connection. Raises TradeValidationError on failure.
    """
    ticker = ticker.upper()
    if side not in ("buy", "sell"):
        raise TradeValidationError(f"Invalid side: {side}")
    if quantity <= 0:
        raise TradeValidationError("Quantity must be positive")

    price = price_cache.get_price(ticker)
    if price is None:
        raise TradeValidationError(f"No price available for {ticker}")

    with get_connection() as conn:
        cash_balance = get_cash_balance(user_id, conn)

        if side == "buy":
            cost = price * quantity
            if cost > cash_balance:
                raise TradeValidationError(
                    f"Insufficient cash: need {cost:.2f}, have {cash_balance:.2f}"
                )
            apply_trade(ticker, side, quantity, price, user_id, conn)
            new_cash_balance = adjust_cash_balance(-cost, user_id, conn)
        else:
            position = get_position(ticker, user_id, conn)
            owned = position.quantity if position else 0.0
            if quantity > owned:
                raise TradeValidationError(
                    f"Insufficient shares: trying to sell {quantity}, own {owned}"
                )
            proceeds = price * quantity
            apply_trade(ticker, side, quantity, price, user_id, conn)
            new_cash_balance = adjust_cash_balance(proceeds, user_id, conn)

        record_trade(ticker, side, quantity, price, user_id, conn)
        total_value = compute_total_value(price_cache, user_id, conn)
        record_snapshot(total_value, user_id, conn)

    return TradeResult(
        ticker=ticker, side=side, quantity=quantity, price=price, cash_balance=new_cash_balance
    )


def compute_total_value(
    price_cache: PriceCache, user_id: str = "default", conn: sqlite3.Connection | None = None
) -> float:
    """Cash balance plus the market value of all open positions."""
    cash_balance = get_cash_balance(user_id, conn)
    positions = list_positions(user_id, conn)
    positions_value = sum(
        (price_cache.get_price(p.ticker) or p.avg_cost) * p.quantity for p in positions
    )
    return cash_balance + positions_value


def positions_with_market_data(price_cache: PriceCache, user_id: str = "default") -> list[dict]:
    """Positions enriched with current price and unrealized P&L."""
    result = []
    for p in list_positions(user_id):
        current_price = price_cache.get_price(p.ticker) or p.avg_cost
        market_value = current_price * p.quantity
        cost_basis = p.avg_cost * p.quantity
        unrealized_pnl = market_value - cost_basis
        pnl_percent = (unrealized_pnl / cost_basis * 100) if cost_basis else 0.0
        result.append(
            {
                "ticker": p.ticker,
                "quantity": p.quantity,
                "avg_cost": p.avg_cost,
                "current_price": current_price,
                "market_value": market_value,
                "unrealized_pnl": unrealized_pnl,
                "unrealized_pnl_percent": pnl_percent,
            }
        )
    return result
