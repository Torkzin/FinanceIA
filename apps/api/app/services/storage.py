import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

ALLOWED_SIGNATURES = {
    ".pdf": (b"%PDF-", "application/pdf"),
    ".png": (b"\x89PNG\r\n\x1a\n", "image/png"),
    ".jpg": (b"\xff\xd8\xff", "image/jpeg"),
    ".jpeg": (b"\xff\xd8\xff", "image/jpeg"),
}

KNOWLEDGE_SIGNATURES = {
    ".pdf": (b"%PDF-", "application/pdf"),
    ".txt": (b"", "text/plain"),
}


@dataclass(frozen=True)
class StoredFile:
    storage_key: str
    media_type: str
    size_bytes: int
    sha256: str


class LocalDocumentStorage:
    def __init__(
        self,
        root: str | Path | None = None,
        *,
        allowed_signatures: dict[str, tuple[bytes, str]] | None = None,
        allowed_message: str = "Only PDF, PNG, JPG, and JPEG files are allowed",
    ) -> None:
        self.root = Path(root or settings.document_storage_path).resolve()
        self.allowed_signatures = allowed_signatures or ALLOWED_SIGNATURES
        self.allowed_message = allowed_message

    async def save(self, upload: UploadFile, company_id: UUID, document_id: UUID) -> StoredFile:
        extension = Path(upload.filename or "").suffix.lower()
        signature = self.allowed_signatures.get(extension)
        if not signature:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=self.allowed_message,
            )

        company_directory = self.root / str(company_id)
        company_directory.mkdir(parents=True, exist_ok=True)
        storage_key = f"{company_id}/{document_id}{extension}"
        destination = self.root / storage_key
        temporary = destination.with_suffix(f"{extension}.tmp")
        maximum_bytes = settings.max_upload_size_mb * 1024 * 1024
        size = 0
        digest = hashlib.sha256()
        first_bytes = b""

        try:
            with temporary.open("wb") as output:
                while chunk := await upload.read(1024 * 1024):
                    if not first_bytes:
                        first_bytes = chunk[:16]
                    size += len(chunk)
                    if size > maximum_bytes:
                        raise HTTPException(
                            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                            detail=f"File exceeds the {settings.max_upload_size_mb} MB limit",
                        )
                    digest.update(chunk)
                    output.write(chunk)

            expected_prefix, media_type = signature
            if size == 0 or not first_bytes.startswith(expected_prefix):
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail="File content does not match its extension",
                )
            os.replace(temporary, destination)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        finally:
            await upload.close()

        return StoredFile(storage_key, media_type, size, digest.hexdigest())

    def resolve(self, storage_key: str) -> Path:
        path = (self.root / storage_key).resolve()
        if self.root not in path.parents:
            raise ValueError("Invalid storage key")
        return path

    def delete(self, storage_key: str) -> None:
        self.resolve(storage_key).unlink(missing_ok=True)


document_storage = LocalDocumentStorage()
knowledge_storage = LocalDocumentStorage(
    settings.knowledge_storage_path,
    allowed_signatures=KNOWLEDGE_SIGNATURES,
    allowed_message="Only searchable PDF and TXT files are allowed",
)
