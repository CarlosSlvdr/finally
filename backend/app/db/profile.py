"""Accessors for the users_profile table."""

from __future__ import annotations

import sqlite3

from .connection import resolve_connection
from .models import Profile
from .seed import DEFAULT_USER_ID


def get_profile(user_id: str = DEFAULT_USER_ID, conn: sqlite3.Connection | None = None) -> Profile:
    """Fetch the user's profile. Raises LookupError if it doesn't exist."""
    with resolve_connection(conn) as c:
        row = c.execute("SELECT * FROM users_profile WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            raise LookupError(f"no profile for user_id={user_id!r}")
        return Profile.from_row(row)


def get_cash_balance(user_id: str = DEFAULT_USER_ID, conn: sqlite3.Connection | None = None) -> float:
    return get_profile(user_id, conn).cash_balance


def adjust_cash_balance(
    delta: float, user_id: str = DEFAULT_USER_ID, conn: sqlite3.Connection | None = None
) -> float:
    """Add `delta` to the cash balance (negative to debit) and return the new balance."""
    with resolve_connection(conn) as c:
        c.execute(
            "UPDATE users_profile SET cash_balance = cash_balance + ? WHERE id = ?",
            (delta, user_id),
        )
        return get_cash_balance(user_id, c)
