import asyncio
import hashlib
from io import BytesIO
from tempfile import SpooledTemporaryFile
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, UploadFile

from pimascor_api.services import storage


def upload_for(payload: bytes) -> UploadFile:
    fileobj = SpooledTemporaryFile(max_size=4, mode="w+b")
    fileobj.write(payload)
    fileobj.seek(0)
    return UploadFile(file=fileobj, filename="receipt.pdf")


def test_document_validation_accepts_boundary_and_rewinds(monkeypatch):
    payload = b"%PDF-123"
    upload = upload_for(payload)
    monkeypatch.setattr(storage, "MAX_DOCUMENT_BYTES", len(payload))
    monkeypatch.setattr(storage, "VALIDATION_CHUNK_BYTES", 5)

    file_name, content_type, digest, size_bytes = asyncio.run(
        storage.read_verified_document(upload)
    )

    assert file_name == "receipt.pdf"
    assert content_type == "application/pdf"
    assert digest == hashlib.sha256(payload).hexdigest()
    assert size_bytes == len(payload)
    assert upload.file.tell() == 0


def test_document_validation_rejects_one_byte_over_limit(monkeypatch):
    payload = b"%PDF-1234"
    upload = upload_for(payload)
    monkeypatch.setattr(storage, "MAX_DOCUMENT_BYTES", len(payload) - 1)
    monkeypatch.setattr(storage, "VALIDATION_CHUNK_BYTES", 5)

    with pytest.raises(HTTPException) as error:
        asyncio.run(storage.read_verified_document(upload))

    assert error.value.status_code == 413
    assert error.value.detail == "Documents must not exceed 100 MB"


def test_configured_limit_is_one_hundred_mebibytes():
    assert storage.MAX_DOCUMENT_BYTES == 100 * 1024 * 1024


def test_put_document_uses_managed_file_object_transfer(monkeypatch):
    calls = {}

    class FakeClient:
        def upload_fileobj(self, fileobj, bucket, key, *, ExtraArgs, Config):
            calls.update(
                payload=fileobj.read(),
                bucket=bucket,
                key=key,
                extra=ExtraArgs,
                config=Config,
            )

    monkeypatch.setattr(storage, "get_settings", lambda: SimpleNamespace(b2_bucket="bridge-ph"))
    monkeypatch.setattr(storage, "s3_client", lambda: FakeClient())
    fileobj = BytesIO(b"%PDF-managed-transfer")
    fileobj.seek(7)

    storage.put_document(
        key="pimascor/demo/documents/test.pdf",
        fileobj=fileobj,
        content_type="application/pdf",
        sha256="abc123",
    )

    assert calls["payload"] == b"%PDF-managed-transfer"
    assert calls["bucket"] == "bridge-ph"
    assert calls["key"] == "pimascor/demo/documents/test.pdf"
    assert calls["extra"] == {
        "ContentType": "application/pdf",
        "Metadata": {"sha256": "abc123"},
    }
    assert calls["config"] is storage.DOCUMENT_TRANSFER_CONFIG
