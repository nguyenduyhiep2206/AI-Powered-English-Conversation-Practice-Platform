from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker ,create_async_engine
from sqlalchemy.orm import declarative_base
from app.core.config import settings
    
engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URL, echo= True)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False, autocommit=False)

Base = declarative_base()

async def init_db():
    import app.models
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
