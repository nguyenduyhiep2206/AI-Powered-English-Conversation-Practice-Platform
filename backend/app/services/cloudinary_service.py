"""Cloudinary storage for book PDFs (uploaded as raw resources)."""

import io

from app.core.config import settings

_configured = False

RESOURCE_TYPE = "raw"


def is_configured() -> bool:
    return bool(
        settings.CLOUDINARY_CLOUD_NAME
        and settings.CLOUDINARY_API_KEY
        and settings.CLOUDINARY_API_SECRET
    )


def _ensure_configured() -> None:
    global _configured
    if _configured:
        return

    if not is_configured():
        raise RuntimeError("Cloudinary is not configured (missing CLOUDINARY_* env vars)")

    import cloudinary

    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,
    )
    _configured = True


def upload_pdf(content: bytes, public_id: str) -> tuple[str, str]:
    """Upload PDF bytes to Cloudinary. Returns (secure_url, public_id)."""
    _ensure_configured()

    import cloudinary.uploader

    result = cloudinary.uploader.upload(
        io.BytesIO(content),
        resource_type=RESOURCE_TYPE,
        folder=settings.CLOUDINARY_BOOK_FOLDER,
        public_id=public_id,
        overwrite=True,
    )
    return result["secure_url"], result["public_id"]


def delete_pdf(public_id: str) -> None:
    """Best-effort removal of a book PDF from Cloudinary."""
    _ensure_configured()

    import cloudinary.uploader

    cloudinary.uploader.destroy(
        public_id,
        resource_type=RESOURCE_TYPE,
        invalidate=True,
    )
