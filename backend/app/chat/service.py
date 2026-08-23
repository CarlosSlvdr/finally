"""Chat orchestration: build prompt, call the LLM (or mock), execute actions, persist history."""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from litellm import completion
from pydantic import ValidationError

from .deps import (
    ChatHistoryReader,
    ChatMessageWriter,
    PortfolioContextProvider,
    TradeError,
    TradeExecutor,
    WatchlistMutator,
)
from .mock import mock_llm_response
from .prompt import build_messages
from .schemas import (
    ChatActions,
    ChatReply,
    ChatTradeAction,
    ChatWatchlistChange,
    ExecutedTrade,
    ExecutedWatchlistChange,
    LLMChatResponse,
)

load_dotenv()

MODEL = "openrouter/openai/gpt-oss-120b"
EXTRA_BODY = {"provider": {"order": ["cerebras"]}}
HISTORY_LIMIT = 10

logger = logging.getLogger(__name__)


def _call_llm(messages: list[dict[str, str]]) -> LLMChatResponse:
    response = completion(
        model=MODEL,
        messages=messages,
        response_format=LLMChatResponse,
        reasoning_effort="low",
        extra_body=EXTRA_BODY,
    )
    content = response.choices[0].message.content
    return LLMChatResponse.model_validate_json(content)


def _execute_trades(
    trades: list[ChatTradeAction], user_id: str, execute_trade: TradeExecutor
) -> list[ExecutedTrade]:
    results = []
    for trade in trades:
        try:
            price = execute_trade(user_id, trade.ticker, trade.side, trade.quantity)
            results.append(
                ExecutedTrade(ticker=trade.ticker, side=trade.side, quantity=trade.quantity, price=price)
            )
        except TradeError as exc:
            results.append(
                ExecutedTrade(
                    ticker=trade.ticker, side=trade.side, quantity=trade.quantity, error=str(exc)
                )
            )
    return results


async def _execute_watchlist_changes(
    changes: list[ChatWatchlistChange],
    user_id: str,
    add_ticker: WatchlistMutator,
    remove_ticker: WatchlistMutator,
) -> list[ExecutedWatchlistChange]:
    results = []
    for change in changes:
        try:
            if change.action == "add":
                await add_ticker(user_id, change.ticker)
            else:
                await remove_ticker(user_id, change.ticker)
            results.append(ExecutedWatchlistChange(ticker=change.ticker, action=change.action))
        except Exception as exc:  # boundary call into another module's mutator
            results.append(
                ExecutedWatchlistChange(ticker=change.ticker, action=change.action, error=str(exc))
            )
    return results


def _append_errors(message: str, actions: ChatActions) -> str:
    errors = [f"{t.side} {t.quantity:g} {t.ticker} failed: {t.error}" for t in actions.trades if t.error]
    errors += [
        f"{c.action} {c.ticker} failed: {c.error}" for c in actions.watchlist_changes if c.error
    ]
    if not errors:
        return message
    return message + "\n\n" + "\n".join(errors)


async def handle_chat_message(
    user_message: str,
    *,
    user_id: str,
    get_portfolio_context: PortfolioContextProvider,
    get_history: ChatHistoryReader,
    save_message: ChatMessageWriter,
    execute_trade: TradeExecutor,
    add_watchlist_ticker: WatchlistMutator,
    remove_watchlist_ticker: WatchlistMutator,
) -> ChatReply:
    if os.environ.get("LLM_MOCK", "false").lower() == "true":
        llm_response = mock_llm_response(user_message)
    else:
        ctx = get_portfolio_context(user_id)
        history = get_history(user_id, HISTORY_LIMIT)
        messages = build_messages(ctx, history, user_message)
        try:
            llm_response = _call_llm(messages)
        except (ValidationError, ValueError) as exc:
            llm_response = LLMChatResponse(
                message=f"Sorry, I had trouble processing that request ({exc}). Please try again."
            )
        except Exception:  # boundary call: litellm/OpenRouter auth, network, rate-limit, etc.
            logger.exception("LLM call failed")
            llm_response = LLMChatResponse(
                message="Sorry, I couldn't reach the AI assistant right now. Please try again shortly."
            )

    actions = ChatActions(
        trades=_execute_trades(llm_response.trades or [], user_id, execute_trade),
        watchlist_changes=await _execute_watchlist_changes(
            llm_response.watchlist_changes or [],
            user_id,
            add_watchlist_ticker,
            remove_watchlist_ticker,
        ),
    )
    final_message = _append_errors(llm_response.message, actions)

    save_message(user_id, "user", user_message, None)
    save_message(user_id, "assistant", final_message, actions.model_dump_json())

    return ChatReply(message=final_message, actions=actions)
