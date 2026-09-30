from io import BytesIO
from uuid import uuid4

import pytest
from fastapi import HTTPException, UploadFile

from app.services.storage import LocalDocumentStorage


@pytest.mark.asyncio
async def test_storage_accepts_png_by_signature(tmp_path) -> None:
    storage = LocalDocumentStorage(tmp_path)
    upload = UploadFile(filename="invoice.png", file=BytesIO(b"\x89PNG\r\n\x1a\ncontent"))

    stored = await storage.save(upload, uuid4(), uuid4())

    assert stored.media_type == "image/png"
    assert stored.size_bytes == 15
    assert len(stored.sha256) == 64
    assert storage.resolve(stored.storage_key).is_file()


@pytest.mark.asyncio
async def test_storage_rejects_extension_content_mismatch(tmp_path) -> None:
    storage = LocalDocumentStorage(tmp_path)
    upload = UploadFile(filename="fake.pdf", file=BytesIO(b"not a real pdf"))

    with pytest.raises(HTTPException) as error:
        await storage.save(upload, uuid4(), uuid4())

    assert error.value.status_code == 415
    assert list(tmp_path.rglob("*.tmp")) == []
