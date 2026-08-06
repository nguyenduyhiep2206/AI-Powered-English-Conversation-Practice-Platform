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

    # After structural validation, LLM-verify spot_error / fix_grammar keys
    SKILL_DRILL_LLM_VERIFY: bool = True

    # Structure: heuristic candidates + optional AI merge before auto-index
    STRUCTURE_AI_MERGE_ENABLED: bool = True
    STRUCTURE_SKIM_LINES_PER_PAGE: int = 5
    STRUCTURE_SKIM_MAX_PAGES: int = 400

    # Skill mini-unit Learn phase (read→check→write→feedback)
    LEARN_UNIT_ENABLED: bool = False
    LEARN_LESSON_MIN_TARGETS: int = 4
    LEARN_LESSON_MAX_TARGETS: int = 7

    # Book unit signal enrichment (attach pipeline)
    UNIT_ENRICH_ENABLED: bool = True
    UNIT_ENRICH_MAX_CHARS: int = 3000
    UNIT_ENRICH_LLM_ENABLED: bool = True

    TUTOR_MAX_USER_TURNS: int = 20
    TUTOR_MAX_MESSAGE_CHARS: int = 2000

    # Tutor RAG + hybrid memory
    TUTOR_RAG_ENABLED: bool = True
    TUTOR_RAG_TOP_K: int = 4
    TUTOR_RAG_MIN_SCORE: float = 0.25
    TUTOR_RAG_MAX_CHARS: int = 2500
    TUTOR_MEMORY_MAX_TURNS: int = 6
    TUTOR_RAG_CACHE_TTL_SECONDS: int = 3600
    TUTOR_RAG_ALWAYS_LIGHT: bool = False
    TUTOR_RAG_CATALOG_LEVEL_FALLBACK: bool = False

    # Lesson Q&A RAG (practice lesson chat)
    LESSON_QA_RAG_ENABLED: bool = True
    LESSON_QA_MEMORY_MAX_TURNS: int = 6


settings = Settings()