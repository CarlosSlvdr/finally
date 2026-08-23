"""Accessors for the portfolio_snapshots table (for the P&L chart)."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

from .connection import resolve_connection
from .models import PortfolioSnapshot
from .seed import DEFAULT_USER_ID


def record_snapshot(
    total_value: float,
    user_id: str = DEFAULT_USER_ID,
    conn: sqlite3.Connection | None = None,
) -> PortfolioSnapshot:
    snapshot_id = str(uuid4())
    now = datetime.now(UTC).isoformat()
    with resolve_connection(conn) as c:
        c.execute(
            "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) "
            "VALUES (?, ?, ?, ?)",
            (snapshot_id, user_id, total_value, now),
        )
    return PortfolioSnapshot(snapshot_id, user_id, total_value, now)


def list_snapshots(
    user_id: str = DEFAULT_USER_ID, conn: sqlite3.Connection | None = None
) -> list[PortfolioSnapshot]:
    """Snapshots oldest-first, ready to plot directly."""
    with resolve_connection(conn) as c:
        rows = c.execute(
            "SELECT * FROM portfolio_snapshots WHERE user_id = ? ORDER BY recorded_at",
            (user_id,),
        ).fetchall()
        return [PortfolioSnapshot.from_row(row) for row in rows]
