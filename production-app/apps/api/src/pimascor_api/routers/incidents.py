from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_db
from ..dependencies import AuthContext, require_csrf
from ..models import (
    IncidentDecision,
    IncidentReport,
    IncidentSource,
    IncidentStatus,
    Role,
    utc_now,
)
from ..schemas import IncidentCreate, IncidentDecisionRequest, IncidentResponse
from ..services.audit import record_audit
from ..services.incidents import (
    deliver_incident_notifications_now,
    incident_reference,
    safe_text,
)


router = APIRouter(prefix="/incidents", tags=["incident reporting"])


@router.post("", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
def report_incident(
    payload: IncidentCreate,
    request: Request,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> IncidentReport:
    existing = db.scalar(
        select(IncidentReport).where(
            IncidentReport.client_report_id == payload.client_report_id,
            IncidentReport.actor_user_id == context.user.id,
        )
    )
    if existing is not None:
        if (
            existing.email_admin_sent_at is None
            or existing.email_developer_sent_at is None
        ):
            deliver_incident_notifications_now(
                db,
                existing,
                context.user,
                settings,
            )
            db.refresh(existing)
        return existing

    incident = IncidentReport(
        client_report_id=payload.client_report_id,
        reference=incident_reference(),
        actor_user_id=context.user.id,
        source=IncidentSource.CLIENT,
        severity=payload.severity,
        operation=safe_text(payload.operation, 160, single_line=True),
        user_action=safe_text(payload.user_action, 500),
        user_message=safe_text(payload.user_message, 800),
        recovery_suggestion=safe_text(payload.recovery_suggestion, 800),
        can_continue=payload.can_continue,
        page_path=safe_text(payload.page_path, 240, single_line=True),
        request_method=safe_text(payload.request_method, 12, single_line=True) or None,
        request_path=safe_text(payload.request_path, 240, single_line=True) or None,
        http_status=payload.http_status,
        error_code=safe_text(payload.error_code, 100, single_line=True),
        technical_summary=safe_text(payload.technical_summary, 4000) or None,
        client_runtime=safe_text(payload.client_runtime, 80, single_line=True) or None,
        deployment_tier=settings.deployment_tier,
        correlation_id=(
            safe_text(payload.correlation_id, 36, single_line=True)
            or getattr(request.state, "correlation_id", None)
        ),
    )
    db.add(incident)
    db.flush()
    record_audit(
        db,
        actor_user_id=context.user.id,
        action="INCIDENT_REPORTED",
        entity_type="incident",
        entity_id=incident.id,
        correlation_id=incident.correlation_id,
        reason=f"{incident.reference} • {incident.operation}",
    )
    db.commit()
    db.refresh(incident)

    deliver_incident_notifications_now(db, incident, context.user, settings)
    db.refresh(incident)
    return incident


@router.post("/{incident_id}/report", response_model=IncidentResponse)
def report_detected_server_incident(
    incident_id: str,
    request: Request,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> IncidentReport:
    incident = db.get(IncidentReport, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="The error report could not be found")
    if (
        incident.actor_user_id is not None
        and incident.actor_user_id != context.user.id
        and context.user.role != Role.ADMIN
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    if (
        incident.email_admin_sent_at is None
        or incident.email_developer_sent_at is None
    ):
        record_audit(
            db,
            actor_user_id=context.user.id,
            action="INCIDENT_REPORTED",
            entity_type="incident",
            entity_id=incident.id,
            correlation_id=getattr(request.state, "correlation_id", None),
            reason=f"{incident.reference} • user requested investigation",
        )
        db.commit()
        deliver_incident_notifications_now(
            db,
            incident,
            context.user,
            settings,
        )
        db.refresh(incident)
    return incident


@router.post("/{incident_id}/decision", response_model=IncidentResponse)
def record_incident_decision(
    incident_id: str,
    payload: IncidentDecisionRequest,
    request: Request,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> IncidentReport:
    incident = db.get(IncidentReport, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="The error report could not be found")
    if (
        incident.actor_user_id is not None
        and incident.actor_user_id != context.user.id
        and context.user.role != Role.ADMIN
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    incident.decision = payload.decision
    incident.decision_note = safe_text(payload.note, 500) or None
    incident.decided_at = utc_now()
    incident.status = (
        IncidentStatus.DISMISSED
        if payload.decision == IncidentDecision.DISMISSED
        else IncidentStatus.CLOSED_BY_USER
    )
    action = {
        IncidentDecision.CONTINUED: "INCIDENT_USER_CONTINUED",
        IncidentDecision.STOPPED: "INCIDENT_USER_STOPPED",
        IncidentDecision.DISMISSED: "INCIDENT_DISMISSED_FALSE_POSITIVE",
    }[payload.decision]
    record_audit(
        db,
        actor_user_id=context.user.id,
        action=action,
        entity_type="incident",
        entity_id=incident.id,
        correlation_id=getattr(request.state, "correlation_id", None),
        reason=incident.reference,
    )
    db.commit()
    db.refresh(incident)
    return incident
