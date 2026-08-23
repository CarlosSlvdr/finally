"""Lazy init: schema creation, seeding, and idempotency."""

from app.db import connection, seed


def test_lazy_init_creates_all_tables():
    db_path = connection.get_db_path()
    assert not db_path.exists()

    with connection.get_connection() as conn:
        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    assert db_path.exists()
    assert tables == {
        "users_profile",
        "watchlist",
        "positions",
        "trades",
        "portfolio_snapshots",
        "chat_messages",
    }


def test_lazy_init_seeds_default_data():
    with connection.get_connection() as conn:
        profile = conn.execute(
            "SELECT * FROM users_profile WHERE id = ?", (seed.DEFAULT_USER_ID,)
        ).fetchone()
        tickers = conn.execute("SELECT ticker FROM watchlist").fetchall()

    assert profile["cash_balance"] == 10000.0
    assert {row["ticker"] for row in tickers} == set(seed.DEFAULT_TICKERS)
    assert len(tickers) == 10


def test_reinit_is_idempotent():
    with connection.get_connection():
        pass

    # Second open must not duplicate seed rows or error on existing tables.
    with connection.get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) AS n FROM watchlist").fetchone()["n"]
        profile_count = conn.execute("SELECT COUNT(*) AS n FROM users_profile").fetchone()["n"]

    assert count == 10
    assert profile_count == 1


def test_db_path_honors_env_override(monkeypatch, tmp_path):
    custom = tmp_path / "nested" / "custom.db"
    monkeypatch.setenv("FINALLY_DB_PATH", str(custom))

    assert connection.get_db_path() == custom
    with connection.get_connection():
        pass
    assert custom.exists()
