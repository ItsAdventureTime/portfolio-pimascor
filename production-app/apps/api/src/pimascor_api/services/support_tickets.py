from __future__ import annotations

import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from ..config import Settings
from ..models import (
    Role,
    SupportTicket,
    SupportTicketAttachment,
    SupportTicketPortalToken,
    SupportTicketReply,
    SupportTicketStatus,
    User,
    UserStatus,
    utc_now,
)
from ..schemas import SupportTicketAttachmentResponse, SupportTicketUserResponse
from ..security import hash_secret
from .email import get_email_provider
from .incidents import safe_text
from .storage import (
    build_support_attachment_key,
    delete_document,
    put_document,
    read_verified_support_attachment,
    storage_configured,
)


logger = logging.getLogger("pimascor.support_tickets")

SUPPORT_STAFF_KEY = "support_staff"
BRIDGE_ADMIN_KEY = "bridge_admin"
REQUESTER_KEY = "requester"
PORTAL_AUDIENCE_SUPPORT = "support"
PORTAL_AUDIENCE_REQUESTER = "requester"


def support_ticket_number() -> str:
    return f"SUP-{utc_now():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}"


def clean_ticket_category(value: str) -> str:
    category = safe_text(value, 80, single_line=True).strip().upper()
    if len(category) < 2:
        raise ValueError("Choose a support category")
    return category


def clean_ticket_reason(value: str) -> str:
    reason = safe_text(value, 160, single_line=True).strip().upper()
    if len(reason) < 2:
        raise ValueError("Choose the reason that best matches your question")
    return reason


def clean_ticket_subject(value: str) -> str:
    subject = safe_text(value, 200, single_line=True)
    if len(subject) < 2:
        raise ValueError("The ticket subject must contain at least two characters")
    return subject


def clean_ticket_message(value: str) -> str:
    message = safe_text(value, 10000)
    if len(message) < 2:
        raise ValueError("The ticket message must contain at least two characters")
    return message


def clean_reply_body(value: str) -> str:
    body = safe_text(value, 10000)
    if len(body) < 2:
        raise ValueError("The reply must contain at least two characters")
    return body


def simulated_reply_body(value: str, *, is_internal: bool, settings: Settings) -> tuple[str, bool]:
    body = clean_reply_body(value)
    if settings.deployment_tier != "demo" or is_internal:
        return body, False
    if body.startswith("[DEMO SIMULATED REPLY]"):
        return body, True
    return f"[DEMO SIMULATED REPLY]\n{body}", True


def validate_status_transition(current: SupportTicketStatus, target: SupportTicketStatus) -> None:
    if current == target:
        return
    allowed: dict[SupportTicketStatus, set[SupportTicketStatus]] = {
        SupportTicketStatus.OPEN: {
            SupportTicketStatus.IN_PROGRESS,
            SupportTicketStatus.RESOLVED,
            SupportTicketStatus.CLOSED,
        },
        SupportTicketStatus.IN_PROGRESS: {
            SupportTicketStatus.WAITING_FOR_REQUESTER,
            SupportTicketStatus.RESOLVED,
            SupportTicketStatus.CLOSED,
        },
        SupportTicketStatus.WAITING_FOR_REQUESTER: {
            SupportTicketStatus.IN_PROGRESS,
            SupportTicketStatus.RESOLVED,
            SupportTicketStatus.CLOSED,
        },
        SupportTicketStatus.RESOLVED: {
            SupportTicketStatus.OPEN,
            SupportTicketStatus.CLOSED,
        },
        SupportTicketStatus.CLOSED: {SupportTicketStatus.OPEN},
    }
    if target not in allowed[current]:
        raise ValueError(f"A ticket cannot move from {current.value} to {target.value}")


def status_audit_action(status: SupportTicketStatus) -> str:
    return {
        SupportTicketStatus.OPEN: "SUPPORT_TICKET_REOPENED",
        SupportTicketStatus.IN_PROGRESS: "SUPPORT_TICKET_STARTED",
        SupportTicketStatus.WAITING_FOR_REQUESTER: "SUPPORT_TICKET_WAITING_FOR_REQUESTER",
        SupportTicketStatus.RESOLVED: "SUPPORT_TICKET_RESOLVED",
        SupportTicketStatus.CLOSED: "SUPPORT_TICKET_CLOSED",
    }[status]


def support_role_response(key: str) -> SupportTicketUserResponse:
    label = "Support Staff" if key == SUPPORT_STAFF_KEY else "Bridge Admin"
    username = "support-staff" if key == SUPPORT_STAFF_KEY else "bridge-admin"
    return SupportTicketUserResponse(
        id=f"portal:{key}",
        username=username,
        display_name=label,
        role=Role.ADMIN,
    )


def _user_response(user: User | None, *, label: str | None = None) -> SupportTicketUserResponse:
    if user is not None:
        return SupportTicketUserResponse.model_validate(user)
    return SupportTicketUserResponse(
        id=f"portal:{label or 'support'}",
        username=(label or "support").lower().replace(" ", "-"),
        display_name=label or "Support Staff",
        role=Role.ADMIN,
    )


def _attachment_response(
    attachment: SupportTicketAttachment,
    *,
    allow_available: bool,
) -> SupportTicketAttachmentResponse:
    return SupportTicketAttachmentResponse(
        id=attachment.id,
        file_name=attachment.file_name,
        content_type=attachment.content_type,
        size_bytes=attachment.size_bytes,
        sha256=attachment.sha256,
        uploaded_by_label=attachment.uploaded_by_label,
        simulated=attachment.simulated,
        created_at=attachment.created_at,
        available=allow_available and attachment.deleted_at is None,
    )


def ticket_response(
    ticket: SupportTicket,
    *,
    support_view: bool,
    portal_url: str | None = None,
) -> dict:
    visible_replies = [reply for reply in ticket.replies if support_view or not reply.is_internal]
    visible_reply_ids = {reply.id for reply in visible_replies}
    initial_attachments = [
        _attachment_response(
            attachment,
            allow_available=ticket.status != SupportTicketStatus.CLOSED,
        )
        for attachment in ticket.attachments
        if attachment.reply_id is None
    ]
    assigned_to = (
        support_role_response(ticket.assigned_to_key)
        if ticket.assigned_to_key
        else (_user_response(ticket.assigned_to) if ticket.assigned_to else None)
    )
    replies = []
    for reply in visible_replies:
        author = _user_response(reply.author, label=reply.author_label)
        reply_attachments = [
            _attachment_response(
                attachment,
                allow_available=ticket.status != SupportTicketStatus.CLOSED,
            )
            for attachment in ticket.attachments
            if attachment.reply_id == reply.id and reply.id in visible_reply_ids
        ]
        replies.append(
            {
                "id": reply.id,
                "body": reply.body,
                "author": author,
                "is_internal": reply.is_internal,
                "is_simulated": reply.is_simulated,
                "created_at": reply.created_at,
                "attachments": reply_attachments,
            }
        )
    return {
        "id": ticket.id,
        "ticket_number": ticket.ticket_number,
        "subject": ticket.subject,
        "category": ticket.category,
        "reason": ticket.reason,
        "message": ticket.message,
        "message_attachments": initial_attachments,
        "requester": _user_response(ticket.requester),
        "requester_role": ticket.requester_role,
        "deployment_tier": ticket.deployment_tier,
        "status": ticket.status,
        "assigned_to": assigned_to,
        "assigned_to_key": ticket.assigned_to_key,
        "replies": replies,
        "version": ticket.version,
        "resolved_at": ticket.resolved_at,
        "closed_at": ticket.closed_at,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at,
        "email_admin_sent_at": ticket.email_admin_sent_at,
        "email_developer_sent_at": ticket.email_developer_sent_at,
        "portal_url": portal_url,
    }


def portal_url(settings: Settings, ticket_id: str, raw_token: str) -> str:
    base_url = settings.public_app_url.rstrip("/") + "/"
    return f"{base_url}#support-portal?ticket={quote(ticket_id)}&token={quote(raw_token)}"


def _portal_recipients(ticket: SupportTicket, settings: Settings) -> list[dict[str, str | None]]:
    return [
        {
            "key": BRIDGE_ADMIN_KEY,
            "email": settings.incident_admin_email,
            "label": "Bridge Admin",
            "audience": PORTAL_AUDIENCE_SUPPORT,
            "user_id": None,
        },
        {
            "key": SUPPORT_STAFF_KEY,
            "email": settings.incident_developer_email,
            "label": "Support Staff",
            "audience": PORTAL_AUDIENCE_SUPPORT,
            "user_id": None,
        },
        {
            "key": REQUESTER_KEY,
            "email": ticket.requester.email,
            "label": ticket.requester.display_name,
            "audience": PORTAL_AUDIENCE_REQUESTER,
            "user_id": ticket.requester_id,
        },
    ]


def rotate_portal_tokens(
    db: Session,
    ticket: SupportTicket,
    settings: Settings,
    *,
    preserve_key: str | None = None,
) -> dict[str, str]:
    now = utc_now()
    for token in ticket.portal_tokens:
        if token.revoked_at is None and token.recipient_key != preserve_key:
            token.revoked_at = now
    raw_tokens: dict[str, str] = {}
    for recipient in _portal_recipients(ticket, settings):
        key = str(recipient["key"])
        if key == preserve_key:
            continue
        raw_token = secrets.token_urlsafe(32)
        raw_tokens[key] = raw_token
        db.add(
            SupportTicketPortalToken(
                ticket_id=ticket.id,
                token_hash=hash_secret(raw_token),
                audience=str(recipient["audience"]),
                recipient_key=key,
                recipient_email=str(recipient["email"]),
                recipient_label=str(recipient["label"]),
                recipient_user_id=recipient["user_id"],
                expires_at=now + timedelta(days=settings.support_portal_token_ttl_days),
            )
        )
    return raw_tokens


def resolve_portal_token(
    db: Session,
    ticket_id: str,
    raw_token: str | None,
) -> tuple[SupportTicket, SupportTicketPortalToken]:
    if not raw_token or len(raw_token) > 200:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="This support link is not valid")
    token = db.scalar(
        select(SupportTicketPortalToken).where(
            SupportTicketPortalToken.ticket_id == ticket_id,
            SupportTicketPortalToken.token_hash == hash_secret(raw_token),
        )
    )
    expires_at = token.expires_at.replace(tzinfo=timezone.utc) if token and token.expires_at.tzinfo is None else token.expires_at if token else None
    if (
        token is None
        or token.revoked_at is not None
        or expires_at <= utc_now()
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="This support link has expired")
    ticket = db.get(SupportTicket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support ticket not found")
    token.last_used_at = utc_now()
    token.use_count += 1
    return ticket, token


async def store_support_attachments(
    db: Session,
    ticket: SupportTicket,
    uploads: list[UploadFile],
    *,
    settings: Settings,
    uploaded_by_label: str,
    uploaded_by_user_id: str | None,
    reply: SupportTicketReply | None = None,
) -> list[SupportTicketAttachment]:
    uploads = [upload for upload in uploads if upload.filename]
    if len(uploads) > settings.support_max_attachments_per_message:
        raise HTTPException(
            status_code=422,
            detail=f"Attach no more than {settings.support_max_attachments_per_message} files to one message",
        )
    if settings.deployment_tier == "production" and not storage_configured():
        raise HTTPException(status_code=503, detail="Support attachment storage is not configured")
    stored: list[SupportTicketAttachment] = []
    try:
        for upload in uploads:
            file_name, content_type, digest, size_bytes = await read_verified_support_attachment(
                upload,
                max_bytes=settings.support_max_attachment_bytes,
            )
            attachment = SupportTicketAttachment(
                id=str(uuid.uuid4()),
                ticket_id=ticket.id,
                reply_id=reply.id if reply else None,
                uploaded_by_user_id=uploaded_by_user_id,
                uploaded_by_label=uploaded_by_label,
                file_name=file_name,
                content_type=content_type,
                size_bytes=size_bytes,
                sha256=digest,
                simulated=settings.deployment_tier == "demo" or not storage_configured(),
            )
            if not attachment.simulated:
                attachment.storage_key = build_support_attachment_key(
                    ticket_id=ticket.id,
                    attachment_id=attachment.id,
                    extension="." + file_name.rsplit(".", 1)[-1],
                    uploaded_at=attachment.created_at or utc_now(),
                )
                await run_in_threadpool(
                    put_document,
                    key=attachment.storage_key,
                    fileobj=upload.file,
                    content_type=content_type,
                    sha256=digest,
                )
            db.add(attachment)
            stored.append(attachment)
    except Exception:
        for attachment in stored:
            if attachment.storage_key:
                try:
                    await run_in_threadpool(delete_document, attachment.storage_key)
                except Exception:
                    logger.exception("Could not clean up a partial support attachment upload")
        raise
    return stored


def purge_ticket_attachments(db: Session, ticket: SupportTicket) -> bool:
    complete = True
    for attachment in ticket.attachments:
        if attachment.deleted_at is not None:
            continue
        if attachment.storage_key:
            try:
                delete_document(attachment.storage_key)
            except Exception:
                complete = False
                logger.exception("Could not delete support attachment %s", attachment.id)
                continue
        attachment.deleted_at = utc_now()
    return complete


def purge_deleted_ticket_attachments(db: Session) -> bool:
    """Retry storage deletion for attachments whose ticket already closed."""
    complete = True
    attachments = db.scalars(
        select(SupportTicketAttachment).where(
            SupportTicketAttachment.deleted_at.is_(None),
            SupportTicketAttachment.storage_key.is_not(None),
            SupportTicketAttachment.ticket_id.in_(
                select(SupportTicket.id).where(SupportTicket.status == SupportTicketStatus.CLOSED)
            ),
        )
    ).all()
    for attachment in attachments:
        try:
            delete_document(attachment.storage_key)
            attachment.deleted_at = utc_now()
        except Exception:
            complete = False
            logger.exception("Could not retry deletion of support attachment %s", attachment.id)
    return complete


def _notification_description(event: str) -> str:
    return {
        "created": "A new support ticket was submitted.",
        "reply": "A new message was added to the support ticket.",
        "assigned": "The support ticket assignment changed.",
        "viewed": "Support has started reviewing the ticket.",
        "resolved": "The support ticket was marked resolved.",
        "closed": "The support ticket was closed.",
        "auto_closed": "The support ticket was closed after seven days without a reply.",
    }.get(event, "The support ticket was updated.")


def _notification_message(
    ticket: SupportTicket,
    *,
    event: str,
    recipient_label: str,
    actor_label: str | None,
    secure_url: str | None,
) -> str:
    link = secure_url or "Use the secure support link from your most recent PIMASCOR email."
    apology = (
        "We’re sorry that we did not receive a reply in time. If you still need help, please submit a new support ticket.\n\n"
        if event == "auto_closed"
        else ""
    )
    return f"""Hi {safe_text(recipient_label, 120, single_line=True)},

PIMASCOR support update

Ticket: {safe_text(ticket.ticket_number, 40, single_line=True)}
Category: {safe_text(ticket.category, 80, single_line=True)}
Reason: {safe_text(ticket.reason, 160, single_line=True)}
Subject: {safe_text(ticket.subject, 200, single_line=True)}
Status: {ticket.status.value.replace('_', ' ').title()}
{_notification_description(event)}
{f"Updated by: {safe_text(actor_label, 80, single_line=True)}" if actor_label else ""}

{apology}Open the secure support thread:
{link}

This link is private to its recipient, expires, and can be revoked. Do not forward it.
Attachments remain private and are removed when the ticket is closed.
"""


def _notification_subject(ticket: SupportTicket, event: str) -> str:
    return f"PIMASCOR support {event.replace('_', ' ')}: {ticket.ticket_number}"


def send_support_ticket_notifications(
    ticket: SupportTicket,
    *,
    event: str,
    actor_label: str | None,
    settings: Settings,
    portal_tokens: dict[str, str],
) -> dict[str, datetime | None]:
    if settings.deployment_tier != "production" or not settings.incident_email_enabled:
        return {}
    try:
        provider = get_email_provider(settings)
    except Exception as exc:
        logger.error("Support ticket email provider unavailable (%s)", type(exc).__name__)
        return {}

    sent: dict[str, datetime | None] = {}
    for recipient in _portal_recipients(ticket, settings):
        key = str(recipient["key"])
        raw_token = portal_tokens.get(key)
        secure_url = portal_url(settings, ticket.id, raw_token) if raw_token else None
        try:
            provider.send_message(
                str(recipient["email"]),
                _notification_subject(ticket, event),
                _notification_message(
                    ticket,
                    event=event,
                    recipient_label=str(recipient["label"]),
                    actor_label=actor_label,
                    secure_url=secure_url,
                ),
                idempotency_key=f"support-ticket/{event}/{ticket.id}/{ticket.version}/{key}",
            )
            sent[key] = utc_now()
        except Exception as exc:
            logger.error(
                "Support ticket email failed for %s recipient %s (%s)",
                ticket.ticket_number,
                key,
                type(exc).__name__,
            )
            sent[key] = None
    return sent


def deliver_support_ticket_notifications_now(
    db: Session,
    ticket: SupportTicket,
    *,
    actor: User | None,
    actor_label: str | None = None,
    settings: Settings,
    reply: SupportTicketReply | None = None,
    event: str | None = None,
    preserve_recipient_key: str | None = None,
    portal_tokens: dict[str, str] | None = None,
) -> None:
    current_tokens = portal_tokens or rotate_portal_tokens(
        db,
        ticket,
        settings,
        preserve_key=preserve_recipient_key,
    )
    db.flush()
    db.commit()
    sent = send_support_ticket_notifications(
        ticket,
        event=event or ("reply" if reply is not None else "created"),
        actor_label=actor_label or (actor.display_name if actor else None),
        settings=settings,
        portal_tokens=current_tokens,
    )
    if sent.get(BRIDGE_ADMIN_KEY) is not None:
        ticket.email_admin_sent_at = sent[BRIDGE_ADMIN_KEY]
    if sent.get(SUPPORT_STAFF_KEY) is not None:
        ticket.email_developer_sent_at = sent[SUPPORT_STAFF_KEY]
    db.commit()


def auto_close_stale_tickets(db: Session, settings: Settings) -> int:
    purge_deleted_ticket_attachments(db)
    cutoff = utc_now() - timedelta(days=settings.support_auto_close_days)
    tickets = db.scalars(
        select(SupportTicket).where(
            SupportTicket.status != SupportTicketStatus.CLOSED,
            SupportTicket.updated_at < cutoff,
        )
    ).all()
    closed = 0
    for ticket in tickets:
        ticket.status = SupportTicketStatus.CLOSED
        ticket.closed_at = utc_now()
        ticket.closure_reason = "AUTO_CLOSED_NO_REPLY"
        ticket.version += 1
        purge_ticket_attachments(db, ticket)
        closed += 1
    if closed:
        db.commit()
        for ticket in tickets:
            deliver_support_ticket_notifications_now(
                db,
                ticket,
                actor=None,
                actor_label="System",
                settings=settings,
                event="auto_closed",
            )
    return closed
