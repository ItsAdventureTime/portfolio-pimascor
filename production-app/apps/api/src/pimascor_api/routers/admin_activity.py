from collections import Counter, defaultdict
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import AuthContext, roles_allowed
from ..models import AuditEvent, Role, User, utc_now
from ..schemas import (
    AdminActivityActor,
    AdminActivityActorSummary,
    AdminActivityCategoryCount,
    AdminActivityEvent,
    AdminActivityResponse,
    AdminActivityTimelinePoint,
)
from ..services.audit import record_audit


router = APIRouter(prefix="/admin/activity", tags=["administration"])
MANILA = ZoneInfo("Asia/Manila")
QUERY_CAP = 5001

ACTION_LABELS = {
    "AUTH_PASSWORD_REJECTED": "Password sign-in rejected",
    "AUTH_EMAIL_CODE_REJECTED": "Email verification rejected",
    "AUTH_LOGIN_SUCCEEDED": "Signed in successfully",
    "AUTH_LOGOUT": "Signed out",
    "AUTH_EMAIL_CHALLENGE_CREATED": "Email verification started",
    "BUDGET_REQUEST_CREATED": "Budget request created",
    "BUDGET_REQUEST_SUBMITTED": "Budget request submitted",
    "BUDGET_REQUEST_APPROVED": "Budget request approved",
    "BUDGET_REQUEST_REJECTED": "Budget request rejected",
    "DCS_PAYMENT_RECORDED": "Actual payment recorded",
    "DCS_PAYMENT_HOLD": "Payment placed on hold",
    "DCS_PAYMENT_RETURN": "Payment returned for clarification",
    "DCS_PAYMENT_RESUME": "Payment resumed",
    "DCS_PAYMENT_NOTE": "Payment note added",
    "FUNDS_RELEASED": "Funds release recorded",
    "FUNDING_SOURCE_CREATED": "Approved funding source added",
    "FUNDING_SOURCE_UPDATED": "Approved funding source changed",
    "LIQUIDATION_SUBMITTED": "Liquidation submitted",
    "LIQUIDATION_CLOSED": "Liquidation closed",
    "BILLING_FINALIZED": "Billing record finalized",
    "BILLING_SUBMITTED_FOR_GM_APPROVAL": "Billing sent to the GM",
    "BILLING_APPROVED_BY_GM": "Billing approved by the GM",
    "BILLING_REJECTED_BY_GM": "Billing returned by the GM",
    "BILLING_REPLACEMENT_PROPOSED_FOR_GM_APPROVAL": "Replacement Billing proposed",
    "BILLING_VOIDED": "Billing record voided",
    "CLIENT_PAYMENT_RECORDED": "Client payment recorded",
    "DOCUMENT_UPLOADED": "Supporting document uploaded",
    "CONFIDENTIAL_DOCUMENT_VIEWED": "Confidential supporting document viewed",
    "ADMIN_ACTIVITY_VIEWED": "Activity monitor viewed",
    "INCIDENT_REPORTED": "User sent an app problem for investigation",
    "INCIDENT_SERVER_DETECTED": "App protected a technical error reference",
    "INCIDENT_USER_CONTINUED": "User continued after a warning",
    "INCIDENT_USER_STOPPED": "User stopped after a warning",
    "INCIDENT_DISMISSED_FALSE_POSITIVE": "User marked a warning as a false detection",
}


def _category(action: str) -> str:
    if action.startswith("INCIDENT_"):
        return "INCIDENT"
    if action.startswith(("AUTH_", "CLI_USER_", "ADMIN_ACTIVITY_")):
        return "SECURITY"
    if action.startswith(("FUNDING_SOURCE_", "TAX_PROFILE_", "CLIENT_")) and not action.startswith(
        "CLIENT_PAYMENT_"
    ):
        return "CONFIGURATION"
    if "DOCUMENT" in action or action.endswith("_UPLOADED"):
        return "DOCUMENT"
    if action.startswith(
        (
            "DCS_PAYMENT_",
            "FUNDS_RELEASED",
            "CLIENT_PAYMENT_",
            "BILLING_",
            "CREDIT_MEMO_",
        )
    ):
        return "TRANSACTION"
    return "WORKFLOW"


def _severity(action: str) -> str:
    if action in {"INCIDENT_REPORTED", "INCIDENT_SERVER_DETECTED"}:
        return "CRITICAL"
    if action == "INCIDENT_USER_STOPPED":
        return "WARNING"
    if action in {
        "BILLING_VOIDED",
        "FUNDING_SOURCE_CREATED",
        "FUNDING_SOURCE_UPDATED",
        "CLI_USER_DISABLED",
        "CLI_USER_PASSWORD_CHANGED",
    }:
        return "CRITICAL"
    if "REJECTED" in action or action in {"DCS_PAYMENT_HOLD", "DCS_PAYMENT_RETURN"}:
        return "WARNING"
    if action.endswith(("SUCCEEDED", "APPROVED", "FINALIZED", "CLOSED", "RECORDED")):
        return "SUCCESS"
    return "INFO"


def _label(action: str) -> str:
    return ACTION_LABELS.get(action, action.replace("_", " ").lower().capitalize())


@router.get("", response_model=AdminActivityResponse)
def admin_activity(
    request: Request,
    days: int = Query(default=30, ge=1, le=90),
    include_admin: bool = Query(default=False),
    category: str | None = Query(
        default=None,
        pattern=r"^(SECURITY|TRANSACTION|WORKFLOW|CONFIGURATION|DOCUMENT|INCIDENT)$",
    ),
    search: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=100, ge=10, le=250),
    context: AuthContext = Depends(roles_allowed(Role.ADMIN)),
    db: Session = Depends(get_db),
) -> AdminActivityResponse:
    today = utc_now().astimezone(MANILA).date()
    start_day = today - timedelta(days=days - 1)
    start = datetime.combine(start_day, time.min, tzinfo=MANILA).astimezone(timezone.utc)
    statement = (
        select(AuditEvent, User)
        .outerjoin(User, AuditEvent.actor_user_id == User.id)
        .where(AuditEvent.occurred_at >= start)
        .order_by(AuditEvent.occurred_at.desc())
    )
    if not include_admin:
        statement = statement.where(or_(User.id.is_(None), User.role != Role.ADMIN))
    rows = db.execute(statement.limit(QUERY_CAP)).all()

    filtered: list[tuple[AuditEvent, User | None]] = []
    needle = search.strip().casefold() if search else ""
    for event, actor in rows:
        event_category = _category(event.action)
        if category and event_category != category:
            continue
        if needle:
            haystack = " ".join(
                (
                    event.action,
                    _label(event.action),
                    event.entity_type,
                    event.entity_id,
                    event.reason or "",
                    actor.display_name if actor else "system",
                    actor.username if actor else "",
                    actor.role.value if actor else "",
                )
            ).casefold()
            if needle not in haystack:
                continue
        filtered.append((event, actor))

    category_counts = Counter(_category(event.action) for event, _ in filtered)
    sensitive = sum(_severity(event.action) in {"WARNING", "CRITICAL"} for event, _ in filtered)
    transaction_events = category_counts["TRANSACTION"]

    actor_groups: dict[str, dict[str, object]] = {}
    for event, actor in filtered:
        if actor is None:
            continue
        group = actor_groups.setdefault(
            actor.id,
            {"actor": actor, "total": 0, "sensitive": 0, "last_seen_at": event.occurred_at},
        )
        group["total"] = int(group["total"]) + 1
        group["sensitive"] = int(group["sensitive"]) + int(
            _severity(event.action) in {"WARNING", "CRITICAL"}
        )

    daily: dict[object, Counter[str]] = defaultdict(Counter)
    for event, _ in filtered:
        local_date = event.occurred_at.astimezone(MANILA).date()
        daily[local_date]["total"] += 1
        daily[local_date][_category(event.action).lower()] += 1

    timeline = []
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        values = daily[day]
        timeline.append(
            AdminActivityTimelinePoint(
                date=day,
                total=values["total"],
                security=values["security"],
                transactions=values["transaction"],
                workflow=values["workflow"],
                configuration=values["configuration"],
                documents=values["document"],
                incidents=values["incident"],
            )
        )

    events = [
        AdminActivityEvent(
            id=event.id,
            actor=AdminActivityActor.model_validate(actor) if actor else None,
            action=event.action,
            label=_label(event.action),
            category=_category(event.action),
            severity=_severity(event.action),
            entity_type=event.entity_type,
            entity_id=event.entity_id,
            reason=event.reason,
            correlation_id=event.correlation_id,
            occurred_at=event.occurred_at,
        )
        for event, actor in filtered[:limit]
    ]

    response = AdminActivityResponse(
        range_days=days,
        include_admin=include_admin,
        total_events=len(filtered),
        sensitive_events=sensitive,
        transaction_events=transaction_events,
        active_users=len(actor_groups),
        last_event_at=filtered[0][0].occurred_at if filtered else None,
        timeline=timeline,
        categories=[
            AdminActivityCategoryCount(category=name, count=category_counts[name])
            for name in (
                "SECURITY",
                "TRANSACTION",
                "WORKFLOW",
                "CONFIGURATION",
                "DOCUMENT",
                "INCIDENT",
            )
        ],
        actors=[
            AdminActivityActorSummary(
                actor=AdminActivityActor.model_validate(group["actor"]),
                total=int(group["total"]),
                sensitive=int(group["sensitive"]),
                last_seen_at=group["last_seen_at"],
            )
            for group in sorted(actor_groups.values(), key=lambda item: int(item["total"]), reverse=True)
        ],
        events=events,
        truncated=len(rows) == QUERY_CAP,
    )

    record_audit(
        db,
        actor_user_id=context.user.id,
        action="ADMIN_ACTIVITY_VIEWED",
        entity_type="audit_monitor",
        entity_id=context.user.id,
        correlation_id=getattr(request.state, "correlation_id", None),
        reason=f"range={days}; include_admin={include_admin}",
    )
    db.commit()
    return response
