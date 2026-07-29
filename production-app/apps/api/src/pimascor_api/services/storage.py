from __future__ import annotations

import hashlib
import re
from functools import lru_cache
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

import boto3
from boto3.s3.transfer import TransferConfig
from botocore.client import Config
from fastapi import HTTPException, UploadFile

from ..config import get_settings


MAX_DOCUMENT_BYTES = 100 * 1024 * 1024
VALIDATION_CHUNK_BYTES = 1024 * 1024
DOCUMENT_TRANSFER_CONFIG = TransferConfig(
    multipart_threshold=16 * 1024 * 1024,
    multipart_chunksize=16 * 1024 * 1024,
    max_concurrency=2,
    use_threads=True,
)
ALLOWED_SIGNATURES = {
    ".pdf": ("application/pdf", lambda value: value.startswith(b"%PDF-")),
    ".jpg": ("image/jpeg", lambda value: value.startswith(b"\xff\xd8\xff")),
    ".jpeg": ("image/jpeg", lambda value: value.startswith(b"\xff\xd8\xff")),
    ".png": ("image/png", lambda value: value.startswith(b"\x89PNG\r\n\x1a\n")),
}


def storage_configured() -> bool:
    settings = get_settings()
    return all(
        (
            settings.b2_endpoint_url,
            settings.b2_region,
            settings.b2_bucket,
            settings.b2_object_prefix,
            settings.b2_key_id_file,
            settings.b2_application_key_file,
        )
    )


def require_storage() -> None:
    if not storage_configured():
        raise HTTPException(status_code=503, detail="Private document storage is not configured")


@lru_cache
def s3_client():
    settings = get_settings()
    require_storage()
    return boto3.client(
        "s3",
        endpoint_url=settings.b2_endpoint_url,
        region_name=settings.b2_region,
        aws_access_key_id=settings.b2_key_id_value,
        aws_secret_access_key=settings.b2_application_key_value,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


async def read_verified_document(upload: UploadFile) -> tuple[str, str, str, int]:
    original_name = Path(upload.filename or "").name.strip()
    extension = Path(original_name).suffix.lower()
    if not original_name or extension not in ALLOWED_SIGNATURES:
        raise HTTPException(status_code=422, detail="Upload a PDF, JPEG, or PNG document")
    first_chunk = await upload.read(VALIDATION_CHUNK_BYTES)
    if not first_chunk:
        raise HTTPException(status_code=422, detail="The uploaded document is empty")
    content_type, signature_check = ALLOWED_SIGNATURES[extension]
    if not signature_check(first_chunk):
        raise HTTPException(status_code=422, detail="The file contents do not match its extension")

    digest = hashlib.sha256()
    digest.update(first_chunk)
    size_bytes = len(first_chunk)
    if size_bytes > MAX_DOCUMENT_BYTES:
        raise HTTPException(status_code=413, detail="Documents must not exceed 100 MB")
    while chunk := await upload.read(VALIDATION_CHUNK_BYTES):
        size_bytes += len(chunk)
        if size_bytes > MAX_DOCUMENT_BYTES:
            raise HTTPException(status_code=413, detail="Documents must not exceed 100 MB")
        digest.update(chunk)

    await upload.seek(0)
    return original_name[:240], content_type, digest.hexdigest(), size_bytes


def build_document_key(*, evidence_id: str, liquidation_id: str, extension: str, uploaded_at) -> str:
    settings = get_settings()
    prefix = (settings.b2_object_prefix or "").strip("/")
    safe_liquidation_id = re.sub(r"[^a-zA-Z0-9-]", "", liquidation_id)
    safe_evidence_id = re.sub(r"[^a-zA-Z0-9-]", "", evidence_id) or str(uuid4())
    return (
        f"{prefix}/documents/liquidations/{safe_liquidation_id}/"
        f"{uploaded_at:%Y/%m}/{safe_evidence_id}{extension.lower()}"
    )


def build_quotation_key(*, quotation_id: str, extension: str, uploaded_at) -> str:
    settings = get_settings()
    prefix = (settings.b2_object_prefix or "").strip("/")
    safe_id = re.sub(r"[^a-zA-Z0-9-]", "", quotation_id) or str(uuid4())
    return f"{prefix}/documents/quotations/{safe_id}/{uploaded_at:%Y/%m}/signed{extension.lower()}"


def build_payment_proof_key(*, source_type: str, record_id: str, extension: str, uploaded_at) -> str:
    settings = get_settings()
    prefix = (settings.b2_object_prefix or "").strip("/")
    safe_source = re.sub(r"[^a-zA-Z0-9-]", "", source_type)
    safe_id = re.sub(r"[^a-zA-Z0-9-]", "", record_id) or str(uuid4())
    return f"{prefix}/documents/payments/{safe_source}/{safe_id}/{uploaded_at:%Y/%m}/proof{extension.lower()}"


def put_document(
    *, key: str, fileobj: BinaryIO, content_type: str, sha256: str
) -> None:
    settings = get_settings()
    fileobj.seek(0)
    s3_client().upload_fileobj(
        fileobj,
        settings.b2_bucket,
        key,
        ExtraArgs={"ContentType": content_type, "Metadata": {"sha256": sha256}},
        Config=DOCUMENT_TRANSFER_CONFIG,
    )


def delete_document(key: str) -> None:
    settings = get_settings()
    if storage_configured():
        s3_client().delete_object(Bucket=settings.b2_bucket, Key=key)


def open_document(*, key: str, byte_range: str | None = None):
    settings = get_settings()
    arguments = {"Bucket": settings.b2_bucket, "Key": key}
    if byte_range:
        arguments["Range"] = byte_range
    return s3_client().get_object(**arguments)


def delete_demo_documents() -> None:
    if not storage_configured():
        return
    settings = get_settings()
    prefix = f"{settings.b2_object_prefix.strip('/')}/documents/"
    client = s3_client()
    token = None
    while True:
        kwargs = {"Bucket": settings.b2_bucket, "Prefix": prefix}
        if token:
            kwargs["ContinuationToken"] = token
        page = client.list_objects_v2(**kwargs)
        objects = [{"Key": item["Key"]} for item in page.get("Contents", [])]
        if objects:
            client.delete_objects(Bucket=settings.b2_bucket, Delete={"Objects": objects, "Quiet": True})
        if not page.get("IsTruncated"):
            break
        token = page.get("NextContinuationToken")
