"""Pydantic models for the chat endpoint (PLAN.md section 9)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ChatTradeAction(BaseModel):
    ticker: str
    side: Literal["buy", "sell"]
    quantity: float


class ChatWatchlistChange(BaseModel):
    ticker: str
    action: Literal["add", "remove"]


class LLMChatResponse(BaseModel):
    """Structured output schema requested from the LLM."""

    message: str
    trades: list[ChatTradeAction] | None = None
    watchlist_changes: list[ChatWatchlistChange] | None = None


class ChatRequest(BaseModel):
    message: str


class ExecutedTrade(BaseModel):
    ticker: str
    side: Literal["buy", "sell"]
    quantity: float
    price: float | None = None
    error: str | None = None


class ExecutedWatchlistChange(BaseModel):
    ticker: str
    action: Literal["add", "remove"]
    error: str | None = None


class ChatActions(BaseModel):
    trades: list[ExecutedTrade] = []
    watchlist_changes: list[ExecutedWatchlistChange] = []


class ChatReply(BaseModel):
    message: str
    actions: ChatActions
