from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..dependencies import AuthContext, roles_allowed
from ..db import get_db
from ..models import Role
from ..schemas import BackupCatalogResponse
from ..services.audit import record_audit


router = APIRouter(prefix="/backups", tags=["production backups"])


def _read_catalog(directory: Path) -> list[BackupCatalogResponse]:
    if not directory.is_dir():
        return []
    entries: list[BackupCatalogResponse] = []
    for path in sorted(directory.glob("history/production-*.json"), reverse=True)[:50]:
        try:
            entries.append(BackupCatalogResponse.model_validate(json.loads(path.read_text(encoding="utf-8"))))
        except (OSError, ValueError):
            continue
    return entries


@router.get("", response_model=list[BackupCatalogResponse])
def list_backups(
    request: Request,
    context: AuthContext = Depends(roles_allowed(Role.ADMIN, Role.DCS)),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[BackupCatalogResponse]:
    """Expose non-sensitive completion metadata; recovery stays CLI-only."""
    entries = _read_catalog(settings.backup_catalog_dir)
    record_audit(
        db,
        actor_user_id=context.user.id,
        action="BACKUP_CATALOG_VIEWED",
        entity_type="backup_catalog",
        entity_id="production",
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    return entries
