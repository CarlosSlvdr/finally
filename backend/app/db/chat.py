"""Accessors for the chat_messages table."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

from .connection import resolve_connection
from .models import ChatMessage
from .seed import DEFAULT_USER_ID


def add_message(
    role: str,
    content: str,
    actions: str | None = None,
    user_id: str = DEFAULT_USER_ID,
    conn: sqlite3.Connection | None = None,
) -> ChatMessage:
    """Append a message. `actions` is a JSON string describing trades/watchlist
    changes executed for this message (assistant messages only), or None."""
    message_id = str(uuid4())
    now = datetime.now(UTC).isoformat()
    with resolve_connection(conn) as c:
        c.execute(
            "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (message_id, user_id, role, content, actions, now),
        )
    return ChatMessage(message_id, user_id, role, content, actions, now)


def list_recent_messages(
    user_id: str = DEFAULT_USER_ID,
    limit: int = 20,
    conn: sqlite3.Connection | None = None,
) -> list[ChatMessage]:
    """The last `limit` messages, oldest-first (ready to feed to the LLM as history)."""
    with resolve_connection(conn) as c:
        rows = c.execute(
            "SELECT * FROM chat_messages WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [ChatMessage.from_row(row) for row in reversed(rows)]
