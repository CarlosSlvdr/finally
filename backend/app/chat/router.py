"""POST /api/chat endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.db.seed import DEFAULT_USER_ID

from .schemas import ChatReply, ChatRequest
from .service import handle_chat_message
from .wiring import (
    build_portfolio_context,
    make_trade_executor,
    make_watchlist_mutator,
    read_chat_history,
    save_chat_message,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("")
async def post_chat(body: ChatRequest, request: Request) -> ChatReply:
    price_cache = request.app.state.price_cache
    market_source = request.app.state.market_source

    return await handle_chat_message(
        body.message,
        user_id=DEFAULT_USER_ID,
        get_portfolio_context=lambda user_id: build_portfolio_context(price_cache, user_id),
        get_history=read_chat_history,
        save_message=save_chat_message,
        execute_trade=make_trade_executor(price_cache),
        add_watchlist_ticker=make_watchlist_mutator(market_source, "add"),
        remove_watchlist_ticker=make_watchlist_mutator(market_source, "remove"),
    )
