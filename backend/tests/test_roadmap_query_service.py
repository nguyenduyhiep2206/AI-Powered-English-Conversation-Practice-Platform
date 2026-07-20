"""Unit helpers for get_user_roadmap (empty path)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from app.services.roadmap_assembler_service import get_user_roadmap


def test_get_user_roadmap_empty():
    db = AsyncMock()
    result = MagicMock()
    result.all.return_value = []
    db.execute = AsyncMock(return_value=result)

    weeks = asyncio.run(get_user_roadmap(db, user_id=1))
    assert weeks == []
