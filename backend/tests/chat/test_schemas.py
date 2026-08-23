import pytest
from pydantic import ValidationError

from app.chat.schemas import LLMChatResponse


def test_message_only_response_is_valid():
    resp = LLMChatResponse.model_validate_json('{"message": "hello"}')
    assert resp.message == "hello"
    assert resp.trades is None
    assert resp.watchlist_changes is None


def test_full_response_with_trades_and_watchlist_changes():
    payload = (
        '{"message": "done", '
        '"trades": [{"ticker": "AAPL", "side": "buy", "quantity": 10}], '
        '"watchlist_changes": [{"ticker": "PYPL", "action": "add"}]}'
    )
    resp = LLMChatResponse.model_validate_json(payload)
    assert resp.trades[0].ticker == "AAPL"
    assert resp.watchlist_changes[0].action == "add"


def test_invalid_side_raises_validation_error():
    payload = '{"message": "x", "trades": [{"ticker": "AAPL", "side": "hold", "quantity": 1}]}'
    with pytest.raises(ValidationError):
        LLMChatResponse.model_validate_json(payload)


def test_missing_message_raises_validation_error():
    with pytest.raises(ValidationError):
        LLMChatResponse.model_validate_json('{"trades": []}')


def test_malformed_json_raises():
    with pytest.raises(ValidationError):
        LLMChatResponse.model_validate_json("not json")
