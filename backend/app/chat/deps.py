"""Dependency contracts the chat service needs from backend-engineer and database-engineer.

Defined as Protocols so the chat service can be built and unit tested against
fakes now, then wired to the real db/portfolio modules once they land in
`app/db/` and `app/api/` (see `app/chat/wiring.py`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PositionContext:
    ticker: str
    quantity: float
    avg_cost: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_percent: float


@dataclass(frozen=True)
class WatchlistContext:
    ticker: str
    current_price: float | None


@dataclass(frozen=True)
class PortfolioContext:
    cash_balance: float
    total_value: float
    positions: list[PositionContext]
    watchlist: list[WatchlistContext]


@dataclass(frozen=True)
class ChatHistoryEntry:
    role: str
    content: str


class TradeError(Exception):
    """Raised by the trade executor when a trade fails validation (e.g. insufficient cash/shares)."""


class PortfolioContextProvider(Protocol):
    def __call__(self, user_id: str) -> PortfolioContext: ...


class TradeExecutor(Protocol):
    def __call__(self, user_id: str, ticker: str, side: str, quantity: float) -> float:
        """Execute a trade and return the fill price. Raises TradeError on failure."""


class WatchlistMutator(Protocol):
    async def __call__(self, user_id: str, ticker: str) -> None: ...


class ChatHistoryReader(Protocol):
    def __call__(self, user_id: str, limit: int) -> list[ChatHistoryEntry]: ...


class ChatMessageWriter(Protocol):
    def __call__(self, user_id: str, role: str, content: str, actions: str | None) -> None: ...
