from __future__ import annotations

from pathlib import Path
import re

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..config import Settings, get_settings
from ..db import get_db
from ..dependencies import AuthContext, get_auth_context, require_csrf
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
from ..schemas import (
    SupportPortalResponse,
    SupportTicketAction,
    SupportTicketAssignment,
    SupportTicketCreate,
    SupportTicketReplyCreate,
    SupportTicketResponse,
    SupportTicketStatusUpdate,
)
from ..services.audit import record_audit
from ..services.storage import open_document
from ..services.support_tickets import (
    BRIDGE_ADMIN_KEY,
    PORTAL_AUDIENCE_REQUESTER,
    PORTAL_AUDIENCE_SUPPORT,
    REQUESTER_KEY,
    SUPPORT_STAFF_KEY,
    clean_reply_body,
    clean_ticket_category,
    clean_ticket_message,
    clean_ticket_reason,
    clean_ticket_subject,
    deliver_support_ticket_notifications_now,
    portal_url,
    purge_ticket_attachments,
    resolve_portal_token,
    simulated_reply_body,
    status_audit_action,
    store_support_attachments,
    support_ticket_number,
    ticket_response,
    validate_status_transition,
    rotate_portal_tokens,
)


router = APIRouter(prefix="/support-tickets", tags=["support tickets"])


def _is_admin(context: AuthContext) -> bool:
    return context.user.role == Role.ADMIN


def _require_admin(context: AuthContext) -> None:
    if not _is_admin(context):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")


def _ticket_query(ticket_id: str):
    return (
        select(SupportTicket)
        .execution_options(populate_existing=True)
        .options(
            selectinload(SupportTicket.requester),
            selectinload(SupportTicket.assigned_to),
            selectinload(SupportTicket.replies).selectinload(SupportTicketReply.author),
            selectinload(SupportTicket.attachments),
            selectinload(SupportTicket.portal_tokens),
        )
        .where(SupportTicket.id == ticket_id)
    )


def _load_ticket(ticket_id: str, context: AuthContext, db: Session) -> SupportTicket:
    ticket = db.execute(_ticket_query(ticket_id)).unique().scalar_one_or_none()
    if ticket is None:
        raise HTTPException(status_code=404, detail="Support ticket not found")
    if not _is_admin(context) and ticket.requester_id != context.user.id:
        raise HTTPException(status_code=403, detail="Permission denied")
    return ticket


def _load_ticket_by_id(ticket_id: str, db: Session) -> SupportTicket:
    ticket = db.execute(_ticket_query(ticket_id)).unique().scalar_one_or_none()
    if ticket is None:
        raise HTTPException(status_code=404, detail="Support ticket not found")
    return ticket


def _response(ticket: SupportTicket, *, support_view: bool, url: str | None = None) -> SupportTicketResponse:
    return SupportTicketResponse(**ticket_response(ticket, support_view=support_view, portal_url=url))


def _check_version(ticket: SupportTicket, expected_version: int | None) -> None:
    if expected_version is not None and expected_version != ticket.version:
        raise HTTPException(status_code=409, detail="This ticket changed after you opened it")


def _set_status(
    ticket: SupportTicket,
    target: SupportTicketStatus,
    *,
    expected_version: int | None,
    actor_user_id: str | None,
    actor_label: str,
    request: Request,
    db: Session,
    closure_reason: str | None = None,
) -> bool:
    _check_version(ticket, expected_version)
    try:
        validate_status_transition(ticket.status, target)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if ticket.status == target:
        return False
    now = utc_now()
    ticket.status = target
    ticket.version += 1
    ticket.closure_reason = closure_reason
    if target == SupportTicketStatus.RESOLVED:
        ticket.resolved_at = now
        ticket.closed_at = None
    elif target == SupportTicketStatus.CLOSED:
        ticket.closed_at = now
    else:
        ticket.resolved_at = None
        ticket.closed_at = None
    record_audit(
        db,
        actor_user_id=actor_user_id,
        action=status_audit_action(target),
        entity_type="support_ticket",
        entity_id=ticket.id,
        correlation_id=getattr(request.state, "correlation_id", None),
        reason=f"{ticket.ticket_number} • {actor_label}",
    )
    return True


async def _parse_form_or_json(request: Request, model):
    try:
        content_type = (request.headers.get("content-type") or "").lower()
        if content_type.startswith("multipart/form-data"):
            form = await request.form()

            def is_upload(value: object) -> bool:
                return isinstance(value, UploadFile) or (
                    hasattr(value, "filename")
                    and hasattr(value, "read")
                    and hasattr(value, "seek")
                )

            values = {key: value for key, value in form.items() if not is_upload(value)}
            uploads = [
                item for item in form.getlist("attachments") if is_upload(item) and item.filename
            ]
            return model.model_validate(values), uploads
        return model.model_validate(await request.json()), []
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The support message needs attention before it can be sent.",
        ) from exc


def _portal_token_from_request(request: Request) -> str | None:
    return request.headers.get("X-Support-Token")


def _load_portal_context(ticket_id: str, request: Request, db: Session):
    ticket, token = resolve_portal_token(db, ticket_id, _portal_token_from_request(request))
    ticket = _load_ticket_by_id(ticket.id, db)
    return ticket, token


def _portal_response(ticket: SupportTicket, token: SupportTicketPortalToken) -> SupportPortalResponse:
    return SupportPortalResponse(
        **ticket_response(ticket, support_view=token.audience == PORTAL_AUDIENCE_SUPPORT),
        viewer_label=token.recipient_label,
        viewer_audience=token.audience,
        can_reply=ticket.status != SupportTicketStatus.CLOSED,
        can_manage=token.audience == PORTAL_AUDIENCE_SUPPORT,
        token_expires_at=token.expires_at,
    )


def _support_actor(token: SupportTicketPortalToken) -> tuple[str | None, Role, str]:
    return token.recipient_user_id, Role.ADMIN, token.recipient_label


@router.post("", response_model=SupportTicketResponse, status_code=201)
async def create_ticket(
    request: Request,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SupportTicketResponse:
    try:
        payload, uploads = await _parse_form_or_json(request, SupportTicketCreate)
        category = clean_ticket_category(payload.category)
        reason = clean_ticket_reason(payload.reason)
        subject = clean_ticket_subject(payload.subject)
        message = clean_ticket_message(payload.message)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    ticket = SupportTicket(
        ticket_number=support_ticket_number(),
        category=category,
        reason=reason,
        subject=subject,
        message=message,
        requester_id=context.user.id,
        requester_role=context.user.role,
        deployment_tier=settings.deployment_tier,
    )
    db.add(ticket)
    db.flush()
    await store_support_attachments(
        db,
        ticket,
        uploads,
        settings=settings,
        uploaded_by_label=context.user.display_name,
        uploaded_by_user_id=context.user.id,
    )
    if settings.deployment_tier == "demo":
        simulated_body, _ = simulated_reply_body(
            "This is a simulated Bridge PH support reply for the demo.",
            is_internal=False,
            settings=settings,
        )
        db.add(
            SupportTicketReply(
                ticket_id=ticket.id,
                author_user_id=None,
                author_role=Role.ADMIN,
                author_label="Bridge Admin",
                body=simulated_body,
                is_simulated=True,
            )
        )
        ticket.version += 1
        record_audit(
            db,
            actor_user_id=context.user.id,
            action="SUPPORT_TICKET_SIMULATED_REPLY",
            entity_type="support_ticket",
            entity_id=ticket.id,
            correlation_id=getattr(request.state, "correlation_id", None),
            reason=ticket.ticket_number,
        )
    record_audit(
        db,
        actor_user_id=context.user.id,
        action="SUPPORT_TICKET_CREATED",
        entity_type="support_ticket",
        entity_id=ticket.id,
        correlation_id=getattr(request.state, "correlation_id", None),
        reason=ticket.ticket_number,
    )
    db.commit()
    ticket = _load_ticket_by_id(ticket.id, db)
    token_values = rotate_portal_tokens(db, ticket, settings)
    deliver_support_ticket_notifications_now(
        db,
        ticket,
        actor=context.user,
        settings=settings,
        event="created",
        portal_tokens=token_values,
    )
    ticket = _load_ticket_by_id(ticket.id, db)
    url = portal_url(settings, ticket.id, token_values[REQUESTER_KEY]) if settings.deployment_tier == "demo" else None
    return _response(ticket, support_view=_is_admin(context), url=url)


@router.get("", response_model=list[SupportTicketResponse])
def list_tickets(
    context: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
    status_filter: SupportTicketStatus | None = Query(default=None, alias="status"),
) -> list[SupportTicketResponse]:
    statement = (
        select(SupportTicket)
        .options(
            selectinload(SupportTicket.requester),
            selectinload(SupportTicket.assigned_to),
            selectinload(SupportTicket.replies).selectinload(SupportTicketReply.author),
            selectinload(SupportTicket.attachments),
        )
        .order_by(SupportTicket.created_at.desc())
    )
    if not _is_admin(context):
        statement = statement.where(SupportTicket.requester_id == context.user.id)
    if status_filter is not None:
        statement = statement.where(SupportTicket.status == status_filter)
    tickets = db.execute(statement).unique().scalars().all()
    return [_response(ticket, support_view=_is_admin(context)) for ticket in tickets]


@router.get("/portal/{ticket_id}", response_model=SupportPortalResponse)
def get_portal_ticket(ticket_id: str, request: Request, db: Session = Depends(get_db)) -> SupportPortalResponse:
    ticket, token = _load_portal_context(ticket_id, request, db)
    changed = False
    if token.audience == PORTAL_AUDIENCE_SUPPORT and ticket.status == SupportTicketStatus.OPEN:
        changed = _set_status(
            ticket,
            SupportTicketStatus.IN_PROGRESS,
            expected_version=None,
            actor_user_id=token.recipient_user_id,
            actor_label=token.recipient_label,
            request=request,
            db=db,
        )
    if changed:
        db.commit()
        deliver_support_ticket_notifications_now(
            db,
            ticket,
            actor=None,
            actor_label=token.recipient_label,
            settings=get_settings(),
            event="viewed",
            preserve_recipient_key=token.recipient_key,
        )
        ticket = _load_ticket_by_id(ticket.id, db)
        token = db.get(SupportTicketPortalToken, token.id) or token
    return _portal_response(ticket, token)


@router.post("/portal/{ticket_id}/replies", response_model=SupportPortalResponse)
async def add_portal_reply(ticket_id: str, request: Request, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> SupportPortalResponse:
    ticket, token = _load_portal_context(ticket_id, request, db)
    if ticket.status == SupportTicketStatus.CLOSED:
        raise HTTPException(status_code=409, detail="This ticket is closed")
    payload, uploads = await _parse_form_or_json(request, SupportTicketReplyCreate)
    body, simulated = simulated_reply_body(payload.body, is_internal=payload.is_internal and token.audience == PORTAL_AUDIENCE_SUPPORT, settings=settings)
    actor_id, actor_role, actor_label = (
        (ticket.requester_id, ticket.requester_role, ticket.requester.display_name)
        if token.audience == PORTAL_AUDIENCE_REQUESTER
        else _support_actor(token)
    )
    is_internal = payload.is_internal and token.audience == PORTAL_AUDIENCE_SUPPORT
    reply = SupportTicketReply(
        ticket_id=ticket.id,
        author_user_id=actor_id,
        author_role=actor_role,
        author_label=actor_label if actor_id is None else None,
        body=clean_reply_body(body),
        is_internal=is_internal,
        is_simulated=simulated,
    )
    db.add(reply)
    db.flush()
    await store_support_attachments(
        db,
        ticket,
        uploads,
        settings=settings,
        uploaded_by_label=actor_label,
        uploaded_by_user_id=actor_id,
        reply=reply,
    )
    if token.audience == PORTAL_AUDIENCE_REQUESTER and ticket.status == SupportTicketStatus.WAITING_FOR_REQUESTER:
        ticket.status = SupportTicketStatus.IN_PROGRESS
    ticket.version += 1
    record_audit(
        db,
        actor_user_id=actor_id,
        action="SUPPORT_TICKET_REPLIED",
        entity_type="support_ticket",
        entity_id=ticket.id,
        correlation_id=getattr(request.state, "correlation_id", None),
        reason=f"{ticket.ticket_number} • {actor_label}",
    )
    db.commit()
    deliver_support_ticket_notifications_now(
        db,
        ticket,
        actor=None,
        actor_label=actor_label,
        settings=settings,
        event="reply" if not is_internal else "updated",
        preserve_recipient_key=token.recipient_key,
    )
    ticket = _load_ticket_by_id(ticket.id, db)
    token = db.get(SupportTicketPortalToken, token.id) or token
    return _portal_response(ticket, token)


@router.post("/portal/{ticket_id}/assignment", response_model=SupportPortalResponse)
def assign_portal_ticket(
    ticket_id: str,
    payload: SupportTicketAssignment,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SupportPortalResponse:
    ticket, token = _load_portal_context(ticket_id, request, db)
    if token.audience != PORTAL_AUDIENCE_SUPPORT:
        raise HTTPException(status_code=403, detail="Permission denied")
    if payload.assigned_to_key is None:
        raise HTTPException(status_code=422, detail="Choose Support Staff or Bridge Admin")
    _check_version(ticket, payload.expected_version)
    if ticket.assigned_to_key != payload.assigned_to_key or ticket.assigned_to_id is not None:
        ticket.assigned_to_key = payload.assigned_to_key
        ticket.assigned_to_id = None
        ticket.version += 1
        record_audit(
            db,
            actor_user_id=token.recipient_user_id,
            action="SUPPORT_TICKET_ASSIGNED",
            entity_type="support_ticket",
            entity_id=ticket.id,
            correlation_id=getattr(request.state, "correlation_id", None),
            reason=f"{ticket.ticket_number} • {payload.assigned_to_key}",
        )
        db.commit()
        deliver_support_ticket_notifications_now(
            db,
            ticket,
            actor=None,
            actor_label=token.recipient_label,
            settings=settings,
            event="assigned",
            preserve_recipient_key=token.recipient_key,
        )
        ticket = _load_ticket_by_id(ticket.id, db)
        token = db.get(SupportTicketPortalToken, token.id) or token
    return _portal_response(ticket, token)


@router.post("/portal/{ticket_id}/status", response_model=SupportPortalResponse)
def update_portal_ticket_status(
    ticket_id: str,
    payload: SupportTicketStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SupportPortalResponse:
    ticket, token = _load_portal_context(ticket_id, request, db)
    if token.audience != PORTAL_AUDIENCE_SUPPORT:
        raise HTTPException(status_code=403, detail="Only support can change ticket status")
    changed = _set_status(
        ticket,
        payload.status,
        expected_version=payload.expected_version,
        actor_user_id=token.recipient_user_id,
        actor_label=token.recipient_label,
        request=request,
        db=db,
    )
    if changed:
        db.commit()
        if payload.status == SupportTicketStatus.CLOSED:
            purge_ticket_attachments(db, ticket)
            db.commit()
        deliver_support_ticket_notifications_now(
            db,
            ticket,
            actor=None,
            actor_label=token.recipient_label,
            settings=settings,
            event="closed" if payload.status == SupportTicketStatus.CLOSED else "resolved" if payload.status == SupportTicketStatus.RESOLVED else "updated",
            preserve_recipient_key=token.recipient_key,
        )
        ticket = _load_ticket_by_id(ticket.id, db)
        token = db.get(SupportTicketPortalToken, token.id) or token
    return _portal_response(ticket, token)


@router.get("/portal/attachments/{attachment_id}")
def get_portal_attachment(attachment_id: str, request: Request, db: Session = Depends(get_db)):
    attachment = db.scalar(select(SupportTicketAttachment).where(SupportTicketAttachment.id == attachment_id))
    if attachment is None:
        raise HTTPException(status_code=404, detail="Attachment not found")
    ticket, token = _load_portal_context(attachment.ticket_id, request, db)
    if token.audience not in {PORTAL_AUDIENCE_SUPPORT, "requester"}:
        raise HTTPException(status_code=403, detail="Permission denied")
    if ticket.status == SupportTicketStatus.CLOSED or attachment.deleted_at is not None:
        raise HTTPException(status_code=410, detail="Attachments are removed when a ticket is closed")
    if attachment.simulated:
        raise HTTPException(status_code=409, detail="Demo attachments are simulated and are not downloadable")
    if not attachment.storage_key:
        raise HTTPException(status_code=404, detail="Attachment content is unavailable")
    try:
        result = open_document(key=attachment.storage_key)
    except Exception as exc:
        raise HTTPException(status_code=404, detail="Attachment content is unavailable") from exc
    safe_name = re.sub(r"[^A-Za-z0-9._ -]", "_", Path(attachment.file_name).name)[:200] or "attachment"
    return StreamingResponse(
        result["Body"].iter_chunks(),
        media_type=attachment.content_type,
        headers={
            "Cache-Control": "no-store, private",
            "Content-Disposition": f'attachment; filename="{safe_name}"',
            "Pragma": "no-cache",
        },
    )


@router.get("/{ticket_id}", response_model=SupportTicketResponse)
def get_ticket(ticket_id: str, context: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)) -> SupportTicketResponse:
    return _response(_load_ticket(ticket_id, context, db), support_view=_is_admin(context))


def _assign_authenticated(
    ticket: SupportTicket,
    payload: SupportTicketAssignment,
    request: Request,
    context: AuthContext,
    db: Session,
) -> None:
    _require_admin(context)
    _check_version(ticket, payload.expected_version)
    assignee = None
    if payload.assigned_to_key is not None:
        ticket.assigned_to_key = payload.assigned_to_key
        ticket.assigned_to_id = None
    elif payload.assigned_to_id is not None:
        assignee = db.scalar(
            select(User).where(
                User.id == payload.assigned_to_id,
                User.role == Role.ADMIN,
                User.status == UserStatus.ACTIVE,
            )
        )
        if assignee is None:
            raise HTTPException(status_code=400, detail="Tickets can only be assigned to an active Admin user")
        ticket.assigned_to_id = payload.assigned_to_id
        ticket.assigned_to_key = None
    else:
        ticket.assigned_to_id = None
        ticket.assigned_to_key = None
    ticket.version += 1
    record_audit(
        db,
        actor_user_id=context.user.id,
        action="SUPPORT_TICKET_ASSIGNED" if assignee or payload.assigned_to_key else "SUPPORT_TICKET_UNASSIGNED",
        entity_type="support_ticket",
        entity_id=ticket.id,
        correlation_id=getattr(request.state, "correlation_id", None),
        reason=f"{ticket.ticket_number} • {payload.assigned_to_key or assignee.display_name if assignee else 'Unassigned'}",
    )


@router.patch("/{ticket_id}/assignment", response_model=SupportTicketResponse)
@router.post("/{ticket_id}/assign", response_model=SupportTicketResponse)
def assign_ticket(
    ticket_id: str,
    payload: SupportTicketAssignment,
    request: Request,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> SupportTicketResponse:
    ticket = _load_ticket(ticket_id, context, db)
    _assign_authenticated(ticket, payload, request, context, db)
    db.commit()
    return _response(_load_ticket(ticket.id, context, db), support_view=_is_admin(context))


def _authenticated_status(ticket_id, target, payload, request, context, db, settings):
    _require_admin(context)
    ticket = _load_ticket(ticket_id, context, db)
    changed = _set_status(ticket, target, expected_version=payload.expected_version if payload else None, actor_user_id=context.user.id, actor_label=context.user.display_name, request=request, db=db)
    if changed:
        db.commit()
        if target == SupportTicketStatus.CLOSED:
            purge_ticket_attachments(db, ticket)
            db.commit()
        deliver_support_ticket_notifications_now(db, ticket, actor=context.user, settings=settings, event="closed" if target == SupportTicketStatus.CLOSED else "resolved" if target == SupportTicketStatus.RESOLVED else "updated")
    return _response(_load_ticket(ticket.id, context, db), support_view=True)


@router.patch("/{ticket_id}/status", response_model=SupportTicketResponse)
def update_ticket_status(ticket_id: str, payload: SupportTicketStatusUpdate, request: Request, context: AuthContext = Depends(require_csrf), db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> SupportTicketResponse:
    return _authenticated_status(ticket_id, payload.status, payload, request, context, db, settings)


@router.post("/{ticket_id}/reopen", response_model=SupportTicketResponse)
def reopen_ticket(ticket_id: str, request: Request, payload: SupportTicketAction | None = None, context: AuthContext = Depends(require_csrf), db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> SupportTicketResponse:
    return _authenticated_status(ticket_id, SupportTicketStatus.OPEN, payload, request, context, db, settings)


@router.post("/{ticket_id}/resolve", response_model=SupportTicketResponse)
def resolve_ticket(ticket_id: str, request: Request, payload: SupportTicketAction | None = None, context: AuthContext = Depends(require_csrf), db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> SupportTicketResponse:
    return _authenticated_status(ticket_id, SupportTicketStatus.RESOLVED, payload, request, context, db, settings)


@router.post("/{ticket_id}/close", response_model=SupportTicketResponse)
def close_ticket(ticket_id: str, request: Request, payload: SupportTicketAction | None = None, context: AuthContext = Depends(require_csrf), db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> SupportTicketResponse:
    return _authenticated_status(ticket_id, SupportTicketStatus.CLOSED, payload, request, context, db, settings)


@router.post("/{ticket_id}/replies", response_model=SupportTicketResponse)
@router.post("/{ticket_id}/reply", response_model=SupportTicketResponse)
async def add_reply(ticket_id: str, request: Request, context: AuthContext = Depends(require_csrf), db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> SupportTicketResponse:
    _require_admin(context)
    ticket = _load_ticket(ticket_id, context, db)
    payload, uploads = await _parse_form_or_json(request, SupportTicketReplyCreate)
    _check_version(ticket, payload.expected_version)
    if ticket.status == SupportTicketStatus.CLOSED:
        raise HTTPException(status_code=409, detail="Reopen the ticket before adding a reply")
    body, is_simulated = simulated_reply_body(payload.body, is_internal=payload.is_internal, settings=settings)
    reply = SupportTicketReply(
        ticket_id=ticket.id,
        author_user_id=context.user.id,
        author_role=context.user.role,
        body=clean_reply_body(body),
        is_internal=payload.is_internal,
        is_simulated=is_simulated,
    )
    db.add(reply)
    db.flush()
    await store_support_attachments(db, ticket, uploads, settings=settings, uploaded_by_label=context.user.display_name, uploaded_by_user_id=context.user.id, reply=reply)
    ticket.version += 1
    record_audit(db, actor_user_id=context.user.id, action="SUPPORT_TICKET_REPLIED", entity_type="support_ticket", entity_id=ticket.id, correlation_id=getattr(request.state, "correlation_id", None), reason=f"{ticket.ticket_number} • {'Internal note' if reply.is_internal else 'Requester-visible reply'}")
    db.commit()
    if not reply.is_internal:
        deliver_support_ticket_notifications_now(db, ticket, actor=context.user, settings=settings, reply=reply)
    return _response(_load_ticket(ticket.id, context, db), support_view=True)
