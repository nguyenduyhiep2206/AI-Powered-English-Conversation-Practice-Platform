"""Supabase Storage for book PDFs."""

from app.core.config import settings

_client = None

SIGNED_URL_EXPIRY_SECONDS = 60 * 60 * 24 * 7  # 7 days


def is_configured() -> bool:
    return bool(settings.SUPABASE_URL and settings.supabase_api_key())


def configuration_error() -> str | None:
    missing = []
    if not settings.SUPABASE_URL:
        missing.append("SUPABASE_URL")
    if not settings.supabase_api_key():
        missing.append("SUPABASE_SERVICE_ROLE_KEY or SUPABASE_SECRET_KEY")
    if missing:
        return f"Missing: {', '.join(missing)}"
    return None


def _get_client():
    global _client
    if _client is not None:
        return _client

    error = configuration_error()
    if error:
        raise RuntimeError(f"Supabase is not configured ({error})")

    from supabase import create_client

    _client = create_client(settings.SUPABASE_URL, settings.supabase_api_key())
    return _client


def _bucket():
    return settings.SUPABASE_BOOK_BUCKET


def upload_pdf(content: bytes, storage_path: str) -> tuple[str, str]:
    """Upload PDF bytes. Returns (file_url, storage_path)."""
    client = _get_client()
    bucket = _bucket()

    client.storage.from_(bucket).upload(
        storage_path,
        content,
        file_options={"content-type": "application/pdf", "upsert": "true"},
    )

    if settings.SUPABASE_BOOK_BUCKET_PUBLIC:
        url = client.storage.from_(bucket).get_public_url(storage_path)
        return url, storage_path

    signed = client.storage.from_(bucket).create_signed_url(
        storage_path,
        SIGNED_URL_EXPIRY_SECONDS,
    )
    url = signed.get("signedURL") or signed.get("signedUrl")
    if not url:
        raise RuntimeError("Supabase did not return a signed URL")
    return url, storage_path


def download_pdf(storage_path: str) -> bytes:
    """Download PDF bytes by storage object path (works with private buckets)."""
    client = _get_client()
    return client.storage.from_(_bucket()).download(storage_path)


def delete_pdf(storage_path: str) -> None:
    """Best-effort removal of a book PDF from Supabase Storage."""
    client = _get_client()
    client.storage.from_(_bucket()).remove([storage_path])
