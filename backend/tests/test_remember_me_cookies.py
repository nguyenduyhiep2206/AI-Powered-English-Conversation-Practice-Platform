from unittest.mock import MagicMock

from app.utils.auth_cookies import set_refresh_token_cookie


def test_set_refresh_cookie_persistent_when_remember_me():
    response = MagicMock()
    set_refresh_token_cookie(response, "tok", remember_me=True)
    kwargs = response.set_cookie.call_args.kwargs
    assert kwargs["value"] == "tok"
    assert kwargs["httponly"] is True
    assert "max_age" in kwargs
    assert kwargs["max_age"] > 0


def test_set_refresh_cookie_session_when_not_remember_me():
    response = MagicMock()
    set_refresh_token_cookie(response, "tok", remember_me=False)
    kwargs = response.set_cookie.call_args.kwargs
    assert kwargs["value"] == "tok"
    assert "max_age" not in kwargs
