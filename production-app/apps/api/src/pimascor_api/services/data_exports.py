from __future__ import annotations

import csv
import hashlib
import logging
import re
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from enum import Enum
from io import TextIOWrapper
from pathlib import Path
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import (
    ApprovalDecision, AuditEvent, Billing, BillingLine, BudgetItem, BudgetRequest,
    BudgetSubmission, Client, ClientPayment, CreditMemo, DataExport, DataExportStatus,
    ExpenseDisbursement, ExpenseRequest, ExpenseValidation, Liquidation, LiquidationEvidence,
    LiquidationLine, PaymentAllocation, PaymentAnnotation, Release, SalesQuotation,
    SalesQuotationLine, TaxProfile, User, utc_now,
)
from ..routers.documents import stored_documents
from .audit import record_audit
from .email import get_email_provider
from .storage import delete_document, open_document, put_document, require_storage


logger = logging.getLogger("pimascor.data_exports")
ARCHIVE_RETENTION = timedelta(hours=1)
EXPORT_MODELS = (
    Client, SalesQuotation, SalesQuotationLine, TaxProfile, BudgetRequest, BudgetItem,
    BudgetSubmission, ApprovalDecision, Release, PaymentAnnotation, ExpenseRequest,
    ExpenseDisbursement, ExpenseValidation, Liquidation, LiquidationLine,
    LiquidationEvidence, Billing, BillingLine, ClientPayment, PaymentAllocation,
    CreditMemo, AuditEvent,
)


def _value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "-", Path(value).name)[:180] or "attachment"


def _csv_rows(db: Session, model: type, excluded: set[str] | None = None) -> tuple[list[str], Iterable[list[str]]]:
    excluded = excluded or set()
    fields = [column.key for column in inspect(model).columns if column.key not in excluded]
    rows = db.scalars(select(model).order_by(*inspect(model).primary_key)).all()
    return fields, ([ _value(getattr(row, field)) for field in fields ] for row in rows)


def _write_csv(archive: zipfile.ZipFile, path: str, db: Session, model: type, excluded: set[str] | None = None) -> None:
    fields, rows = _csv_rows(db, model, excluded)
    with archive.open(path, "w") as raw:
        with TextIOWrapper(raw, encoding="utf-8", newline="") as text:
            writer = csv.writer(text, lineterminator="\n")
            writer.writerow(fields)
            writer.writerows(rows)


def _write_manifest(archive: zipfile.ZipFile, export: DataExport, attachment_count: int) -> None:
    content = (
        "PIMASCOR local records archive\n"
        f"Archive ID: {export.id}\n"
        f"Requested at (UTC): {export.requested_at.isoformat()}\n"
        f"Included attachments: {attachment_count}\n\n"
        "records/ contains UTF-8 CSV files for each operational module.\n"
        "attachments/ contains the original uploaded supporting documents.\n"
        "Security credentials, password hashes, login sessions, and email login challenges are intentionally excluded.\n"
        "The archive is a local records copy, not an accounting-system import or a replacement for a tested disaster-recovery backup.\n"
    )
    archive.writestr("README.txt", content)


def _archive_storage_key(export_id: str) -> str:
    settings = get_settings()
    prefix = (settings.b2_object_prefix or "").strip("/")
    return f"{prefix}/exports/{export_id}/pimascor-records-{export_id}.zip"


def _archive_file_name(export_id: str) -> str:
    return f"pimascor-records-{export_id[:8]}.zip"


def build_export_archive(db: Session, export: DataExport) -> tuple[str, int, str]:
    """Create a portable ZIP without ever exposing an object-storage URL to a browser."""
    require_storage()
    settings = get_settings()
    digest = hashlib.sha256()
    with tempfile.SpooledTemporaryFile(max_size=32 * 1024 * 1024, mode="w+b") as output:
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            _write_manifest(archive, export, len(stored_documents(db)))
            _write_csv(archive, "records/users.csv", db, User, {"password_hash"})
            for model in EXPORT_MODELS:
                _write_csv(archive, f"records/{inspect(model).local_table.name}.csv", db, model)
            for document in stored_documents(db):
                source = open_document(key=document.storage_key)
                body = source["Body"]
                try:
                    attachment_path = f"attachments/{_safe_name(document.id)}-{_safe_name(document.file_name)}"
                    with archive.open(attachment_path, "w") as destination:
                        while chunk := body.read(64 * 1024):
                            destination.write(chunk)
                finally:
                    body.close()
        output.seek(0)
        while chunk := output.read(1024 * 1024):
            digest.update(chunk)
        size = output.tell()
        output.seek(0)
        key = _archive_storage_key(export.id)
        put_document(
            key=key,
            fileobj=output,
            content_type="application/zip",
            sha256=digest.hexdigest(),
        )
    return key, size, digest.hexdigest()


def process_one_export(db: Session) -> bool:
    """Claim and complete one durable export request. Run this from the worker process."""
    export = db.scalar(
        select(DataExport)
        .where(DataExport.status == DataExportStatus.QUEUED)
        .order_by(DataExport.requested_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if export is None:
        return False
    export.status = DataExportStatus.PROCESSING
    export.started_at = utc_now()
    db.commit()
    try:
        key, size, sha256 = build_export_archive(db, export)
        export.status = DataExportStatus.READY
        export.storage_key = key
        export.file_name = _archive_file_name(export.id)
        export.size_bytes = size
        export.sha256 = sha256
        export.completed_at = utc_now()
        export.expires_at = export.completed_at + ARCHIVE_RETENTION
        record_audit(
            db,
            actor_user_id=export.requested_by_id,
            action="DATA_EXPORT_READY",
            entity_type="data_export",
            entity_id=export.id,
            reason="Archive retained for one hour",
        )
        db.commit()
        _notify_ready(export)
    except Exception as exc:
        logger.exception("Data export %s failed", export.id)
        db.rollback()
        export = db.get(DataExport, export.id)
        if export:
            export.status = DataExportStatus.FAILED
            export.error_message = "The archive could not be completed. No download link was sent."
            record_audit(
                db,
                actor_user_id=export.requested_by_id,
                action="DATA_EXPORT_FAILED",
                entity_type="data_export",
                entity_id=export.id,
            )
            db.commit()
    return True


def _notify_ready(export: DataExport) -> None:
    if export.requested_by is None:
        return
    settings = get_settings()
    app_url = settings.public_app_url.rstrip("/") + "/#accounting"
    expiry = export.expires_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if export.expires_at else "one hour"
    get_email_provider(settings).send_message(
        export.requested_by.email,
        "Your PIMASCOR local records archive is ready",
        (
            "Your requested local records archive is ready. Sign in and open Accounting Export to download it.\n\n"
            f"Open PIMASCOR: {app_url}\n"
            f"The archive will be deleted at {expiry}. This email link does not grant access by itself."
        ),
        idempotency_key=f"data-export-ready/{export.id}",
    )


def expire_exports(db: Session) -> int:
    now = utc_now()
    exports = db.scalars(
        select(DataExport).where(
            DataExport.status == DataExportStatus.READY,
            DataExport.expires_at.is_not(None),
            DataExport.expires_at <= now,
        )
    ).all()
    for export in exports:
        if export.storage_key:
            delete_document(export.storage_key)
        export.status = DataExportStatus.EXPIRED
        export.storage_key = None
        record_audit(
            db,
            actor_user_id=export.requested_by_id,
            action="DATA_EXPORT_EXPIRED",
            entity_type="data_export",
            entity_id=export.id,
        )
    if exports:
        db.commit()
    return len(exports)
