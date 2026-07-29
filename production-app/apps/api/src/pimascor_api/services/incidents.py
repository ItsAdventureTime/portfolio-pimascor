from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import PurePath

from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import SessionLocal
from ..models import IncidentReport, User, utc_now
from .email import get_email_provider


logger = logging.getLogger("pimascor.incidents")
CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def safe_text(value: str | None, limit: int, *, single_line: bool = False) -> str:
    cleaned = CONTROL_CHARACTERS.sub("", value or "").strip()
    if single_line:
        cleaned = " ".join(cleaned.split())
    return cleaned[:limit]


def incident_reference() -> str:
    return f"INC-{utc_now():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}"


def safe_trace_summary(exc: Exception) -> str:
    frames: list[str] = []
    traceback = exc.__traceback__
    while traceback is not None:
        frame = traceback.tb_frame
        frames.append(
            f"{PurePath(frame.f_code.co_filename).name}:{traceback.tb_lineno}:{frame.f_code.co_name}"
        )
        traceback = traceback.tb_next
    path = " -> ".join(frames[-12:]) or "No Python frames were available"
    return safe_text(f"Exception type: {type(exc).__name__}\nCall path: {path}", 4000)


@dataclass(frozen=True)
class IncidentEmailSnapshot:
    id: str
    reference: str
    actor_name: str
    actor_role: str
    operation: str
    user_action: str
    user_message: str
    recovery_suggestion: str
    page_path: str
    request_method: str
    request_path: str
    http_status: str
    error_code: str
    technical_summary: str
    client_runtime: str
    deployment_tier: str
    correlation_id: str
    occurred_at: str


def snapshot_incident(incident: IncidentReport, actor: User | None) -> IncidentEmailSnapshot:
    return IncidentEmailSnapshot(
        id=incident.id,
        reference=incident.reference,
        actor_name=actor.display_name if actor else "Signed-out user or system",
        actor_role=actor.role.value if actor else "Not available",
        operation=safe_text(incident.operation, 160, single_line=True),
        user_action=safe_text(incident.user_action, 500),
        user_message=safe_text(incident.user_message, 800),
        recovery_suggestion=safe_text(incident.recovery_suggestion, 800),
        page_path=safe_text(incident.page_path, 240, single_line=True),
        request_method=safe_text(incident.request_method, 12, single_line=True) or "Not available",
        request_path=safe_text(incident.request_path, 240, single_line=True) or "Not available",
        http_status=str(incident.http_status) if incident.http_status is not None else "Not available",
        error_code=safe_text(incident.error_code, 100, single_line=True),
        technical_summary=safe_text(incident.technical_summary, 4000) or "Not available",
        client_runtime=safe_text(incident.client_runtime, 80, single_line=True) or "Not available",
        deployment_tier=safe_text(incident.deployment_tier, 20, single_line=True),
        correlation_id=safe_text(incident.correlation_id, 36, single_line=True) or "Not available",
        occurred_at=incident.created_at.isoformat(),
    )


def _admin_email(snapshot: IncidentEmailSnapshot) -> str:
    return f"""PIMASCOR needs your attention

Reference: {snapshot.reference}
Environment: {snapshot.deployment_tier.title()}
When: {snapshot.occurred_at}
Person: {snapshot.actor_name} ({snapshot.actor_role})

What the person was doing:
{snapshot.user_action}

What happened:
{snapshot.user_message}

Suggested next step:
{snapshot.recovery_suggestion}

Where it happened:
{snapshot.page_path}

Accounting or transaction context:
Operation: {snapshot.operation}
Result code: {snapshot.error_code}

How to check it:
1. Sign in with the appropriate PIMASCOR role.
2. Open the page shown above.
3. Repeat the operation using approved test or demo data.
4. Note whether the same message appears.

This report was sent only after the person selected Report for investigation. It
intentionally excludes passwords, email codes, secret keys, bank details, document
contents, and form values.
"""


def _developer_email(snapshot: IncidentEmailSnapshot) -> str:
    codex_prompt = f"""Investigate and fix PIMASCOR incident {snapshot.reference}.

Goal:
Reproduce the incident, identify the root cause, implement the smallest safe fix,
and verify that the financial workflow and role permissions remain correct.

Context:
- Deployment tier: {snapshot.deployment_tier}
- User operation: {snapshot.operation}
- Page: {snapshot.page_path}
- Request: {snapshot.request_method} {snapshot.request_path}
- HTTP status: {snapshot.http_status}
- Error code: {snapshot.error_code}
- Correlation ID: {snapshot.correlation_id}
- Client runtime: {snapshot.client_runtime}
- Technical summary: {snapshot.technical_summary}

Boundaries:
- Do not expose or request secrets, passwords, email codes, bank details, document
  contents, or production form values.
- Preserve the approved accounting workflow, audit history, role permissions,
  PostgreSQL data, Podman secrets, rootless Quadlets, and Caddy-only public ingress.
- Inspect current source and logs before editing. Do not guess.

Verification:
- Add or update a regression test.
- Run the API test suite and web production build.
- Report the root cause, changed files, verification results, migration impact,
  and safe deployment or rollback steps.
"""
    return f"""PIMASCOR technical incident

Reference: {snapshot.reference}
When: {snapshot.occurred_at}
Actor: {snapshot.actor_name} ({snapshot.actor_role})
Environment: {snapshot.deployment_tier}
Operation: {snapshot.operation}
User action: {snapshot.user_action}
Page: {snapshot.page_path}
Request: {snapshot.request_method} {snapshot.request_path}
HTTP status: {snapshot.http_status}
Error code: {snapshot.error_code}
Correlation ID: {snapshot.correlation_id}
Client runtime: {snapshot.client_runtime}

Safe technical context:
{snapshot.technical_summary}

User-facing message:
{snapshot.user_message}

Suggested recovery:
{snapshot.recovery_suggestion}

Copy into ChatGPT Codex:

{codex_prompt}
"""


def send_incident_notifications(
    snapshot: IncidentEmailSnapshot,
    settings: Settings | None = None,
) -> tuple[datetime | None, datetime | None]:
    settings = settings or get_settings()
    if not settings.incident_email_enabled:
        return None, None
    provider = get_email_provider(settings)
    admin_sent_at: datetime | None = None
    developer_sent_at: datetime | None = None
    try:
        provider.send_message(
            settings.incident_admin_email,
            f"PIMASCOR attention needed: {snapshot.reference}",
            _admin_email(snapshot),
            idempotency_key=f"incident-admin/{snapshot.id}",
        )
        admin_sent_at = utc_now()
    except Exception as exc:
        logger.error(
            "Admin incident email failed for %s (%s)",
            snapshot.reference,
            type(exc).__name__,
        )
    try:
        provider.send_message(
            settings.incident_developer_email,
            f"PIMASCOR technical incident: {snapshot.reference}",
            _developer_email(snapshot),
            idempotency_key=f"incident-developer/{snapshot.id}",
        )
        developer_sent_at = utc_now()
    except Exception as exc:
        logger.error(
            "Developer incident email failed for %s (%s)",
            snapshot.reference,
            type(exc).__name__,
        )
    return admin_sent_at, developer_sent_at


def deliver_incident_notifications(snapshot: IncidentEmailSnapshot) -> None:
    admin_sent_at, developer_sent_at = send_incident_notifications(snapshot)
    if admin_sent_at is None and developer_sent_at is None:
        return
    with SessionLocal.begin() as db:
        incident = db.get(IncidentReport, snapshot.id)
        if incident is None:
            return
        incident.email_admin_sent_at = admin_sent_at
        incident.email_developer_sent_at = developer_sent_at


def deliver_incident_notifications_now(
    db: Session,
    incident: IncidentReport,
    actor: User | None,
    settings: Settings,
) -> None:
    admin_sent_at, developer_sent_at = send_incident_notifications(
        snapshot_incident(incident, actor),
        settings,
    )
    if admin_sent_at is not None:
        incident.email_admin_sent_at = admin_sent_at
    if developer_sent_at is not None:
        incident.email_developer_sent_at = developer_sent_at
    db.commit()
