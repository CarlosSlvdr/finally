"""Deterministic LLM_MOCK=true response logic, for fast/free/reproducible E2E tests.

Matching rules (integration-tester: assert against these exactly):
  - "buy <qty> <TICKER>" or "sell <qty> <TICKER>", case-insensitive -> a trade action.
    Multiple matches in one message all become separate trades, executed in order.
  - "watch <TICKER>" or "add <TICKER>" -> a watchlist "add" action.
  - "unwatch <TICKER>" or "remove <TICKER>" -> a watchlist "remove" action.
  - Anything else -> a plain acknowledgement message with no actions.
Tickers are matched as 1-5 letter words and upper-cased in the output.
"""

from __future__ import annotations

import re

from .schemas import ChatTradeAction, ChatWatchlistChange, LLMChatResponse

_TRADE_RE = re.compile(r"\b(buy|sell)\s+(\d+(?:\.\d+)?)\s+([A-Za-z]{1,5})\b", re.IGNORECASE)
_WATCH_ADD_RE = re.compile(r"\b(?:watch|add)\s+([A-Za-z]{1,5})\b", re.IGNORECASE)
_WATCH_REMOVE_RE = re.compile(r"\b(?:unwatch|remove)\s+([A-Za-z]{1,5})\b", re.IGNORECASE)


def mock_llm_response(user_message: str) -> LLMChatResponse:
    trades = [
        ChatTradeAction(ticker=ticker.upper(), side=side.lower(), quantity=float(qty))
        for side, qty, ticker in _TRADE_RE.findall(user_message)
    ]
    watchlist_changes = [
        ChatWatchlistChange(ticker=ticker.upper(), action="add")
        for ticker in _WATCH_ADD_RE.findall(user_message)
    ] + [
        ChatWatchlistChange(ticker=ticker.upper(), action="remove")
        for ticker in _WATCH_REMOVE_RE.findall(user_message)
    ]

    if trades and watchlist_changes:
        message = "Mock: executed the requested trades and watchlist changes."
    elif trades:
        summary = ", ".join(f"{t.side} {t.quantity:g} {t.ticker}" for t in trades)
        message = f"Mock: executed {summary}."
    elif watchlist_changes:
        message = "Mock: updated your watchlist."
    else:
        message = "Mock response: I received your message."

    return LLMChatResponse(
        message=message,
        trades=trades or None,
        watchlist_changes=watchlist_changes or None,
    )
