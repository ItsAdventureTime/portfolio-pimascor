from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..config import get_settings
from ..dependencies import AuthContext, csrf_roles_allowed, roles_allowed
from ..models import DataExport, DataExportStatus, Role
from ..schemas import DataExportResponse
from ..services.audit import record_audit
from ..services.data_exports import ARCHIVE_RETENTION
from ..services.storage import open_document, require_storage


router = APIRouter(prefix="/data-exports", tags=["local records exports"])
PH_TZ = ZoneInfo("Asia/Manila")
WEEKLY_EXPORT_LIMIT = 2


def response_for(export: DataExport) -> DataExportResponse:
    return DataExportResponse.model_validate(export)


def ph_week_start(now: datetime) -> datetime:
    local_now = now.astimezone(PH_TZ)
    monday = (local_now - timedelta(days=local_now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return monday.astimezone(ZoneInfo("UTC"))


def require_data_exports_enabled() -> None:
    if not get_settings().data_export_enabled:
        raise HTTPException(
            status_code=503,
            detail="Complete local records archives are disabled in this demo environment",
        )


@router.get("", response_model=list[DataExportResponse])
def list_exports(
    _: AuthContext = Depends(roles_allowed(Role.ADMIN, Role.MICH, Role.GM, Role.DCS)),
    db: Session = Depends(get_db),
):
    if not get_settings().data_export_enabled:
        return []
    return db.scalars(
        select(DataExport)
        .options(selectinload(DataExport.requested_by))
        .order_by(DataExport.requested_at.desc())
        .limit(12)
    ).all()


@router.post("", response_model=DataExportResponse, status_code=202)
def request_export(
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.ADMIN, Role.MICH, Role.GM, Role.DCS)),
    db: Session = Depends(get_db),
):
    require_data_exports_enabled()
    require_storage()
    week_start = ph_week_start(datetime.now(PH_TZ))
    used = db.scalars(
        select(DataExport).where(DataExport.requested_at >= week_start)
    ).all()
    if len(used) >= WEEKLY_EXPORT_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Two full-record export requests have already been accepted this Philippine calendar week",
        )
    export = DataExport(requested_by_id=context.user.id)
    db.add(export)
    db.flush()
    record_audit(
        db,
        actor_user_id=context.user.id,
        action="DATA_EXPORT_REQUESTED",
        entity_type="data_export",
        entity_id=export.id,
        correlation_id=getattr(request.state, "correlation_id", None),
        reason="Authorized user requested a complete local records archive",
    )
    db.commit()
    db.refresh(export)
    return db.scalar(
        select(DataExport)
        .options(selectinload(DataExport.requested_by))
        .where(DataExport.id == export.id)
    )


@router.get("/{export_id}/download")
def download_export(
    export_id: str,
    request: Request,
    context: AuthContext = Depends(roles_allowed(Role.ADMIN, Role.MICH, Role.GM, Role.DCS)),
    db: Session = Depends(get_db),
):
    require_data_exports_enabled()
    export = db.scalar(
        select(DataExport)
        .options(selectinload(DataExport.requested_by))
        .where(DataExport.id == export_id)
    )
    if export is None:
        raise HTTPException(status_code=404, detail="Export request not found")
    if export.status != DataExportStatus.READY or not export.storage_key or not export.expires_at:
        raise HTTPException(status_code=409, detail="This archive is not available for download")
    now = datetime.now(ZoneInfo("UTC"))
    if export.expires_at <= now:
        raise HTTPException(status_code=410, detail="This archive has expired and is being deleted")
    stored = open_document(key=export.storage_key)
    body = stored["Body"]
    record_audit(
        db,
        actor_user_id=context.user.id,
        action="DATA_EXPORT_DOWNLOADED",
        entity_type="data_export",
        entity_id=export.id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()

    def content():
        try:
            while chunk := body.read(64 * 1024):
                yield chunk
        finally:
            body.close()

    return StreamingResponse(
        content(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{export.file_name or "pimascor-records.zip"}"',
            "Content-Length": str(stored.get("ContentLength") or export.size_bytes or 0),
            "Cache-Control": "private, no-store, max-age=0",
            "X-Content-Type-Options": "nosniff",
            "X-Robots-Tag": "noindex, nofollow, noarchive",
        },
    )
