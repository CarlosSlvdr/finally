"""Watchlist management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.db.watchlist import add_to_watchlist, list_watchlist, remove_from_watchlist
from app.schemas import WatchlistAddRequest

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


@router.get("")
async def get_watchlist(request: Request) -> list[dict]:
    price_cache = request.app.state.price_cache
    tickers = list_watchlist()
    result = []
    for ticker in tickers:
        update = price_cache.get(ticker)
        result.append(
            {
                "ticker": ticker,
                "price": update.price if update else None,
                "change": update.change if update else None,
                "change_percent": update.change_percent if update else None,
            }
        )
    return result


@router.post("")
async def add_ticker(body: WatchlistAddRequest, request: Request) -> dict:
    ticker = body.ticker.upper()
    add_to_watchlist(ticker)
    await request.app.state.market_source.add_ticker(ticker)
    return {"ticker": ticker}


@router.delete("/{ticker}")
async def remove_ticker(ticker: str, request: Request) -> dict:
    ticker = ticker.upper()
    if ticker not in list_watchlist():
        raise HTTPException(status_code=404, detail=f"{ticker} not in watchlist")
    remove_from_watchlist(ticker)
    await request.app.state.market_source.remove_ticker(ticker)
    return {"ticker": ticker}
