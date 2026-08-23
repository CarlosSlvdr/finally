import pytest

from app.db import profile


def test_get_profile_returns_seeded_default():
    p = profile.get_profile()
    assert p.id == "default"
    assert p.cash_balance == 10000.0


def test_get_cash_balance():
    assert profile.get_cash_balance() == 10000.0


def test_adjust_cash_balance_credit_and_debit():
    new_balance = profile.adjust_cash_balance(-2500.0)
    assert new_balance == 7500.0

    new_balance = profile.adjust_cash_balance(100.0)
    assert new_balance == 7600.0
    assert profile.get_cash_balance() == 7600.0


def test_get_profile_unknown_user_raises():
    with pytest.raises(LookupError):
        profile.get_profile(user_id="ghost")
