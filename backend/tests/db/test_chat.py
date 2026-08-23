from app.db import chat


def test_add_message_defaults_actions_to_none():
    msg = chat.add_message("user", "hello")
    assert msg.role == "user"
    assert msg.content == "hello"
    assert msg.actions is None


def test_add_message_with_actions():
    msg = chat.add_message("assistant", "bought AAPL", actions='{"trades": []}')
    assert msg.actions == '{"trades": []}'


def test_list_recent_messages_oldest_first_and_limited():
    for i in range(5):
        chat.add_message("user", f"message {i}")
    result = chat.list_recent_messages(limit=3)
    assert [m.content for m in result] == ["message 2", "message 3", "message 4"]
