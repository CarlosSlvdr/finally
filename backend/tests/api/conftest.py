"""Fixtures for API tests: isolated sqlite db + TestClient with lifespan."""

from __future__ import annotations

import importlib
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "test_finally.db"
    monkeypatch.setenv("FINALLY_DB_PATH", str(db_path))
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)

    from app import main as main_module

    importlib.reload(main_module)

    with TestClient(main_module.app) as test_client:
        yield test_client


@pytest.fixture
def user_id() -> str:
    return os.environ.get("FINALLY_USER_ID", "default")
