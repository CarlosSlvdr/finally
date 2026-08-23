"""Portfolio and trade execution endpoints."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Request

from app.db.profile import get_cash_balance
from app.db.snapshots import list_snapshots
from app.portfolio_service import (
    TradeValidationError,
    compute_total_value,
    execute_trade,
    positions_with_market_data,
)
from app.schemas import TradeRequest

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("")
async def get_portfolio(request: Request) -> dict:
    price_cache = request.app.state.price_cache
    positions = positions_with_market_data(price_cache)
    cash_balance = get_cash_balance()
    total_value = compute_total_value(price_cache)
    return {
        "cash_balance": cash_balance,
        "positions": positions,
        "total_value": total_value,
    }


@router.post("/trade")
async def post_trade(trade: TradeRequest, request: Request) -> dict:
    price_cache = request.app.state.price_cache
    try:
        result = execute_trade(price_cache, trade.ticker, trade.side, trade.quantity)
    except TradeValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "ticker": result.ticker,
        "side": result.side,
        "quantity": result.quantity,
        "price": result.price,
        "cash_balance": result.cash_balance,
    }


@router.get("/history")
async def get_history() -> list[dict]:
    return [asdict(s) for s in list_snapshots()]
