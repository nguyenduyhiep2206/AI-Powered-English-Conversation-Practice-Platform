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

    # Book uploads (stored on Supabase Storage)
    MAX_BOOK_UPLOAD_MB: int = 50

    # Supabase Storage
    SUPABASE_URL: str
    # Provide either the legacy service_role JWT or the new sb_secret_... key.
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_SECRET_KEY: str = ""  # new dashboard "secret" key (sb_secret_...)
    SUPABASE_BOOK_BUCKET: str = "books"
    SUPABASE_BOOK_BUCKET_PUBLIC: bool = False

    def supabase_api_key(self) -> str:
        return self.SUPABASE_SERVICE_ROLE_KEY or self.SUPABASE_SECRET_KEY

    # MongoDB (optional until indexing pipeline is enabled)
    MONGODB_URL: str
    MONGODB_DB_NAME: str = "englishflow"

    # Voyage AI embeddings (book indexing) — phase 2 after text chunks are saved
    VOYAGE_API_KEY: str
    VOYAGE_EMBEDDING_MODEL: str = "voyage-4-lite"
    VOYAGE_EMBED_BATCH_SIZE: int = 32
    VOYAGE_EMBED_BATCH_DELAY_SECONDS: float = 1.0

    # Quiz generation context (text only; no embeddings required)
    QUIZ_CONTEXT_MAX_CHARS: int = 5000
    OPENAI_API_KEY: str
    OPENAI_MODEL: str
    OPENAI_BASE_URL: str

    # Structure: heuristic candidates + optional AI merge before auto-index
    STRUCTURE_AI_MERGE_ENABLED: bool = True
    STRUCTURE_SKIM_LINES_PER_PAGE: int = 5
    STRUCTURE_SKIM_MAX_PAGES: int = 400

    # Skill mini-unit Learn phase (read→check→write→feedback)
    LEARN_UNIT_ENABLED: bool = False


settings = Settings()