"""Pydantic request/response models for the REST API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TradeRequest(BaseModel):
    ticker: str
    side: str = Field(pattern="^(buy|sell)$")
    quantity: float = Field(gt=0)


class WatchlistAddRequest(BaseModel):
    ticker: str
