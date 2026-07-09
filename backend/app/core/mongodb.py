from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings

_client: AsyncIOMotorClient | None = None


async def connect_mongo() -> None:
    global _client
    if not settings.MONGODB_URL:
        return

    _client = AsyncIOMotorClient(settings.MONGODB_URL)
    await _client.admin.command("ping")


async def disconnect_mongo() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


def get_mongo_db() -> AsyncIOMotorDatabase:
    if _client is None:
        raise RuntimeError("MongoDB is not configured or not connected")
    return _client[settings.MONGODB_DB_NAME]
