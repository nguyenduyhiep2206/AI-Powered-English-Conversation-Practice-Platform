from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str
    DEBUG: bool

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int

    # Google OAuth
    GOOGLE_CLIENT_ID: str

    # Database
    SQLALCHEMY_DATABASE_URL: str

    # Redis
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int = 0

    PERMISSION_CACHE_TTL_SECONDS: int

    # CORS
    FRONTEND_URL: str

    # Book uploads (stored on Cloudinary)
    MAX_BOOK_UPLOAD_MB: int = 50

    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str | None = None
    CLOUDINARY_API_KEY: str | None = None
    CLOUDINARY_API_SECRET: str | None = None
    CLOUDINARY_BOOK_FOLDER: str = "books"

    # MongoDB (optional until indexing pipeline is enabled)
    MONGODB_URL: str | None = None
    MONGODB_DB_NAME: str = "englishflow"


settings = Settings()