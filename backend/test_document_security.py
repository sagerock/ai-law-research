import asyncio

import pytest
from fastapi import HTTPException

from document_security import read_upload_limited, validate_remote_url


class FakeUpload:
    def __init__(self, content: bytes):
        self.content = content
        self.offset = 0

    async def read(self, size: int) -> bytes:
        chunk = self.content[self.offset:self.offset + size]
        self.offset += len(chunk)
        return chunk


def test_read_upload_limited_accepts_boundary_size():
    upload = FakeUpload(b"a" * 10)
    assert asyncio.run(read_upload_limited(upload, max_bytes=10)) == b"a" * 10


def test_read_upload_limited_rejects_before_buffering_rest():
    upload = FakeUpload(b"a" * 20)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(read_upload_limited(upload, max_bytes=10))
    assert exc.value.status_code == 413
    assert upload.offset == 11


@pytest.mark.parametrize("url", [
    "http://storage.example.com/file.pdf",
    "https://user:password@storage.example.com/file.pdf",
    "https://127.0.0.1/file.pdf",
])
def test_validate_remote_url_rejects_unsafe_urls(monkeypatch, url):
    monkeypatch.setenv("OUTLINE_STORAGE_HOSTS", "storage.example.com")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(validate_remote_url(url))
    assert exc.value.status_code == 400


def test_validate_remote_url_fails_closed_without_allowlist(monkeypatch):
    monkeypatch.delenv("OUTLINE_STORAGE_HOSTS", raising=False)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(validate_remote_url("https://storage.example.com/file.pdf"))
    assert exc.value.status_code == 503
