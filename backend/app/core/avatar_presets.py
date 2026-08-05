"""Default avatar presets — keep URLs in sync with frontend/my-app/lib/avatar-presets.ts."""

from __future__ import annotations

import random

AVATAR_PRESET_URLS: tuple[str, ...] = (
    "/avatars/Mask group.png",
    "/avatars/Mask group (1).png",
    "/avatars/Mask group (2).png",
    "/avatars/Mask group (3).png",
    "/avatars/Mask group (4).png",
    "/avatars/Mask group (5).png",
    "/avatars/Mask group (6).png",
    "/avatars/Mask group (7).png",
    "/avatars/Mask group (8).png",
    "/avatars/Mask group (9).png",
    "/avatars/Mask group (10).png",
    "/avatars/Mask group (11).png",
    "/avatars/Mask group (12).png",
    "/avatars/Mask group (13).png",
)


def pick_random_avatar_url() -> str:
    return random.choice(AVATAR_PRESET_URLS)
