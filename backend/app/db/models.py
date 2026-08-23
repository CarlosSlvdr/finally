"""Typed row models for the FinAlly schema (PLAN.md section 7)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Profile:
    id: str
    cash_balance: float
    created_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Profile:
        return cls(id=row["id"], cash_balance=row["cash_balance"], created_at=row["created_at"])


@dataclass(frozen=True, slots=True)
class Position:
    id: str
    user_id: str
    ticker: str
    quantity: float
    avg_cost: float
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Position:
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            ticker=row["ticker"],
            quantity=row["quantity"],
            avg_cost=row["avg_cost"],
            updated_at=row["updated_at"],
        )


@dataclass(frozen=True, slots=True)
class Trade:
    id: str
    user_id: str
    ticker: str
    side: str
    quantity: float
    price: float
    executed_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Trade:
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            ticker=row["ticker"],
            side=row["side"],
            quantity=row["quantity"],
            price=row["price"],
            executed_at=row["executed_at"],
        )


@dataclass(frozen=True, slots=True)
class PortfolioSnapshot:
    id: str
    user_id: str
    total_value: float
    recorded_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> PortfolioSnapshot:
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            total_value=row["total_value"],
            recorded_at=row["recorded_at"],
        )


@dataclass(frozen=True, slots=True)
class ChatMessage:
    id: str
    user_id: str
    role: str
    content: str
    actions: str | None
    created_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> ChatMessage:
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            role=row["role"],
            content=row["content"],
            actions=row["actions"],
            created_at=row["created_at"],
        )
