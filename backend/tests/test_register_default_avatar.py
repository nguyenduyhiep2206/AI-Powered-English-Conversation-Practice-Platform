from app.core.avatar_presets import AVATAR_PRESET_URLS, pick_random_avatar_url
from app.schemas.user_schema import UserCreate
from app.services.auth_service import _build_user_from_register


def test_pick_random_avatar_url_is_known_preset():
    assert pick_random_avatar_url() in AVATAR_PRESET_URLS


def test_register_assigns_default_avatar_when_missing():
    user = _build_user_from_register(
        UserCreate(
            username="newbie",
            email="newbie@example.com",
            password="password1",
            full_name="New Bee",
        )
    )
    assert user.avatar_url in AVATAR_PRESET_URLS


def test_register_keeps_provided_avatar():
    chosen = AVATAR_PRESET_URLS[3]
    user = _build_user_from_register(
        UserCreate(
            username="chooser",
            email="chooser@example.com",
            password="password1",
            full_name="Chooser",
            avatar_url=chosen,
        )
    )
    assert user.avatar_url == chosen
