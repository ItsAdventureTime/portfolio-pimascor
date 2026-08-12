from __future__ import annotations

import logging
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from ..config import Settings
from ..models import SupportTicket, SupportTicketReply, SupportTicketStatus, User, utc_now
from .email import get_email_provider
from .incidents import safe_text


logger = logging.getLogger("pimascor.support_tickets")


def support_ticket_number() -> str:
    return f"SUP-{utc_now():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}"


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


def validate_status_transition(
    current: SupportTicketStatus,
    target: SupportTicketStatus,
) -> None:
    if current == target:
        return
    allowed: dict[SupportTicketStatus, set[SupportTicketStatus]] = {
        SupportTicketStatus.OPEN: {
            SupportTicketStatus.IN_PROGRESS,
            SupportTicketStatus.RESOLVED,
        },
        SupportTicketStatus.IN_PROGRESS: {
            SupportTicketStatus.WAITING_FOR_REQUESTER,
            SupportTicketStatus.RESOLVED,
        },
        SupportTicketStatus.WAITING_FOR_REQUESTER: {
            SupportTicketStatus.IN_PROGRESS,
            SupportTicketStatus.RESOLVED,
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


def _notification_message(
    ticket: SupportTicket,
    *,
    event: str,
    actor: User | None,
    reply: SupportTicketReply | None,
) -> str:
    actor_role = actor.role.value if actor else "SYSTEM"
    if event == "created":
        description = "A new support ticket was submitted."
    else:
        description = "A new support reply was added."
    return f"""PIMASCOR support notification

Ticket: {safe_text(ticket.ticket_number, 40, single_line=True)}
Environment: {safe_text(ticket.deployment_tier, 20, single_line=True)}
Subject: {clean_ticket_subject(ticket.subject)}
Actor role: {safe_text(actor_role, 20, single_line=True)}
{description}

Sign in to PIMASCOR to review the authenticated ticket content. Message bodies,
secrets, passwords, one-time codes, sessions, bank details, and uploaded documents
are intentionally not included in this notification.
"""


def send_support_ticket_notifications(
    ticket: SupportTicket,
    *,
    event: str,
    actor: User | None,
    reply: SupportTicketReply | None = None,
    settings: Settings,
) -> tuple[datetime | None, datetime | None]:
    if settings.deployment_tier != "production" or not settings.incident_email_enabled:
        return None, None

    try:
        provider = get_email_provider(settings)
    except Exception as exc:
        logger.error("Support ticket email provider unavailable (%s)", type(exc).__name__)
        return None, None

    subject = (
        f"PIMASCOR support ticket received: {ticket.ticket_number}"
        if event == "created"
        else f"PIMASCOR support ticket updated: {ticket.ticket_number}"
    )
    notification_id = reply.id if reply is not None else ticket.id
    text = _notification_message(ticket, event=event, actor=actor, reply=reply)
    sent: list[datetime | None] = []
    for destination in (settings.incident_admin_email, settings.incident_developer_email):
        try:
            provider.send_message(
                destination,
                subject,
                text,
                idempotency_key=f"support-ticket/{event}/{notification_id}/{destination}",
            )
            sent.append(utc_now())
        except Exception as exc:
            logger.error(
                "Support ticket email failed for %s (%s)",
                ticket.ticket_number,
                type(exc).__name__,
            )
            sent.append(None)
    return sent[0], sent[1]


def deliver_support_ticket_notifications_now(
    db: Session,
    ticket: SupportTicket,
    *,
    actor: User | None,
    settings: Settings,
    reply: SupportTicketReply | None = None,
) -> None:
    admin_sent_at, developer_sent_at = send_support_ticket_notifications(
        ticket,
        event="reply" if reply is not None else "created",
        actor=actor,
        reply=reply,
        settings=settings,
    )
    target = reply or ticket
    if admin_sent_at is not None:
        target.email_admin_sent_at = admin_sent_at
    if developer_sent_at is not None:
        target.email_developer_sent_at = developer_sent_at
    db.commit()
