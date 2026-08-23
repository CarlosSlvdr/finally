"""SQLite persistence layer for FinAlly (PLAN.md section 7).

Lazy initialization: the first `get_connection()` call creates the schema and
seed data if the database file doesn't exist or is empty. No migrations, no
manual setup.

Public API:
    get_connection, get_db_path      - connection.py: lazy-init connection helper
    Profile, Position, Trade,
    PortfolioSnapshot, ChatMessage   - models.py: typed row dataclasses
    get_profile, get_cash_balance,
    adjust_cash_balance              - profile.py
    list_watchlist, add_to_watchlist,
    remove_from_watchlist            - watchlist.py
    get_position, list_positions,
    apply_trade                      - positions.py
    record_trade, list_trades        - trades.py
    record_snapshot, list_snapshots  - snapshots.py
    add_message, list_recent_messages - chat.py
    DEFAULT_USER_ID                  - seed.py

Every accessor takes an optional `conn` argument. Pass one to compose several
calls into a single atomic transaction (e.g. a trade touching cash, a
position, and the trade log); omit it to run standalone with auto-commit.
"""

from .chat import add_message, list_recent_messages
from .connection import get_connection, get_db_path
from .models import ChatMessage, PortfolioSnapshot, Position, Profile, Trade
from .positions import apply_trade, get_position, list_positions
from .profile import adjust_cash_balance, get_cash_balance, get_profile
from .seed import DEFAULT_USER_ID
from .snapshots import list_snapshots, record_snapshot
from .trades import list_trades, record_trade
from .watchlist import add_to_watchlist, list_watchlist, remove_from_watchlist

__all__ = [
    "get_connection",
    "get_db_path",
    "Profile",
    "Position",
    "Trade",
    "PortfolioSnapshot",
    "ChatMessage",
    "get_profile",
    "get_cash_balance",
    "adjust_cash_balance",
    "list_watchlist",
    "add_to_watchlist",
    "remove_from_watchlist",
    "get_position",
    "list_positions",
    "apply_trade",
    "record_trade",
    "list_trades",
    "record_snapshot",
    "list_snapshots",
    "add_message",
    "list_recent_messages",
    "DEFAULT_USER_ID",
]
