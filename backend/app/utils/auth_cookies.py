from fastapi import Response

from app.core.config import settings

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_MAX_AGE = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600


def set_refresh_token_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        max_age=REFRESH_COOKIE_MAX_AGE,
        samesite="lax",
        secure=not settings.DEBUG,
    )


def clear_refresh_token_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE_NAME)
