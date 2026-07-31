from fastapi import Response

from app.core.config import settings

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_MAX_AGE = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600


def set_refresh_token_cookie(
    response: Response,
    refresh_token: str,
    *,
    remember_me: bool = True,
) -> None:
    """Set httpOnly refresh cookie. Session cookie when remember_me is False."""
    kwargs: dict = {
        "key": REFRESH_COOKIE_NAME,
        "value": refresh_token,
        "httponly": True,
        "samesite": "lax",
        "secure": not settings.DEBUG,
    }
    if remember_me:
        kwargs["max_age"] = REFRESH_COOKIE_MAX_AGE
    response.set_cookie(**kwargs)


def clear_refresh_token_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE_NAME)
