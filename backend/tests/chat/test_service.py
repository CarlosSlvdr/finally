import json

import pytest

import app.chat.service as service


async def test_llm_mock_mode_executes_trade_and_saves_history(monkeypatch, fake_deps):
    monkeypatch.setenv("LLM_MOCK", "true")

    reply = await service.handle_chat_message("buy 5 AAPL", user_id="default", **fake_deps.kwargs())

    assert reply.actions.trades[0].ticker == "AAPL"
    assert reply.actions.trades[0].price == 190.0
    assert fake_deps.cash_balance == pytest.approx(10_000.0 - 190.0 * 5)
    assert fake_deps.saved_messages[0] == ("default", "user", "buy 5 AAPL", None)
    assert fake_deps.saved_messages[1][1] == "assistant"


async def test_trade_failure_is_folded_into_message_not_raised(monkeypatch, fake_deps):
    monkeypatch.setenv("LLM_MOCK", "true")
    fake_deps.fail_trade_error = "insufficient cash"

    reply = await service.handle_chat_message("buy 5 AAPL", user_id="default", **fake_deps.kwargs())

    assert reply.actions.trades[0].error == "insufficient cash"
    assert "insufficient cash" in reply.message


async def test_watchlist_change_executes_via_mutator(monkeypatch, fake_deps):
    monkeypatch.setenv("LLM_MOCK", "true")

    reply = await service.handle_chat_message("watch NVDA", user_id="default", **fake_deps.kwargs())

    assert reply.actions.watchlist_changes[0].ticker == "NVDA"
    assert "NVDA" in fake_deps.watchlist


async def test_non_mock_mode_calls_llm_and_parses_structured_output(monkeypatch, fake_deps):
    monkeypatch.setenv("LLM_MOCK", "false")

    class FakeMessage:
        content = json.dumps(
            {"message": "Bought it.", "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 1}]}
        )

    class FakeChoice:
        message = FakeMessage()

    class FakeResponse:
        choices = [FakeChoice()]

    monkeypatch.setattr(service, "completion", lambda **kwargs: FakeResponse())

    reply = await service.handle_chat_message("buy 1 AAPL", user_id="default", **fake_deps.kwargs())

    assert reply.message == "Bought it."
    assert reply.actions.trades[0].ticker == "AAPL"


async def test_malformed_llm_response_is_handled_gracefully(monkeypatch, fake_deps):
    monkeypatch.setenv("LLM_MOCK", "false")

    class FakeMessage:
        content = "not valid json at all"

    class FakeChoice:
        message = FakeMessage()

    class FakeResponse:
        choices = [FakeChoice()]

    monkeypatch.setattr(service, "completion", lambda **kwargs: FakeResponse())

    reply = await service.handle_chat_message("hello", user_id="default", **fake_deps.kwargs())

    assert "trouble processing" in reply.message
    assert reply.actions.trades == []
    assert reply.actions.watchlist_changes == []


async def test_llm_call_raising_is_handled_gracefully(monkeypatch, fake_deps):
    monkeypatch.setenv("LLM_MOCK", "false")

    def _raise(**kwargs):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(service, "completion", _raise)

    reply = await service.handle_chat_message("hello", user_id="default", **fake_deps.kwargs())

    assert "couldn't reach the AI assistant" in reply.message
    assert reply.actions.trades == []
    assert reply.actions.watchlist_changes == []
