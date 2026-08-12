from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..config import Settings, get_settings
from ..db import get_db
from ..dependencies import AuthContext, get_auth_context, require_csrf
from ..models import Role, SupportTicket, SupportTicketReply, SupportTicketStatus, User, UserStatus, utc_now
from ..schemas import (
    SupportTicketAction,
    SupportTicketAssignment,
    SupportTicketCreate,
    SupportTicketReplyCreate,
    SupportTicketReplyResponse,
    SupportTicketResponse,
    SupportTicketStatusUpdate,
    SupportTicketUserResponse,
)
from ..services.audit import record_audit
from ..services.support_tickets import (
    clean_ticket_message,
    clean_ticket_subject,
    deliver_support_ticket_notifications_now,
    simulated_reply_body,
    status_audit_action,
    support_ticket_number,
    validate_status_transition,
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
        )
        .where(SupportTicket.id == ticket_id)
    )


def _load_ticket(ticket_id: str, context: AuthContext, db: Session) -> SupportTicket:
    ticket = db.scalar(_ticket_query(ticket_id))
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support ticket not found")
    if not _is_admin(context) and ticket.requester_id != context.user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    return ticket


def _user_response(user: User | None) -> SupportTicketUserResponse | None:
    return SupportTicketUserResponse.model_validate(user) if user is not None else None


def _ticket_response(ticket: SupportTicket, *, admin: bool) -> SupportTicketResponse:
    replies = [reply for reply in ticket.replies if admin or not reply.is_internal]
    return SupportTicketResponse(
        id=ticket.id,
        ticket_number=ticket.ticket_number,
        subject=ticket.subject,
        message=ticket.message,
        requester=SupportTicketUserResponse.model_validate(ticket.requester),
        requester_role=ticket.requester_role,
        deployment_tier=ticket.deployment_tier,
        status=ticket.status,
        assigned_to=_user_response(ticket.assigned_to),
        replies=[
            SupportTicketReplyResponse(
                id=reply.id,
                body=reply.body,
                author=SupportTicketUserResponse.model_validate(reply.author),
                is_internal=reply.is_internal,
                is_simulated=reply.is_simulated,
                created_at=reply.created_at,
            )
            for reply in replies
        ],
        version=ticket.version,
        resolved_at=ticket.resolved_at,
        closed_at=ticket.closed_at,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        email_admin_sent_at=ticket.email_admin_sent_at,
        email_developer_sent_at=ticket.email_developer_sent_at,
    )


def _check_version(ticket: SupportTicket, expected_version: int | None) -> None:
    if expected_version is not None and expected_version != ticket.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This ticket changed after you opened it",
        )


def _set_status(
    ticket: SupportTicket,
    target: SupportTicketStatus,
    *,
    expected_version: int | None,
    context: AuthContext,
    request: Request,
    db: Session,
) -> None:
    _check_version(ticket, expected_version)
    try:
        validate_status_transition(ticket.status, target)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if ticket.status == target:
        return
    now = utc_now()
    ticket.status = target
    ticket.version += 1
    if target == SupportTicketStatus.RESOLVED:
        ticket.resolved_at = now
        ticket.closed_at = None
    elif target == SupportTicketStatus.CLOSED:
        ticket.closed_at = now
    elif target == SupportTicketStatus.OPEN:
        ticket.resolved_at = None
        ticket.closed_at = None
    else:
        ticket.resolved_at = None
        ticket.closed_at = None
    record_audit(
        db,
        actor_user_id=context.user.id,
        action=status_audit_action(target),
        entity_type="support_ticket",
        entity_id=ticket.id,
        correlation_id=getattr(request.state, "correlation_id", None),
        reason=ticket.ticket_number,
    )


@router.post("", response_model=SupportTicketResponse, status_code=status.HTTP_201_CREATED)
def create_ticket(
    payload: SupportTicketCreate,
    request: Request,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SupportTicketResponse:
    try:
        subject = clean_ticket_subject(payload.subject)
        message = clean_ticket_message(payload.message)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    ticket = SupportTicket(
        ticket_number=support_ticket_number(),
        subject=subject,
        message=message,
        requester_id=context.user.id,
        requester_role=context.user.role,
        deployment_tier=settings.deployment_tier,
    )
    db.add(ticket)
    db.flush()
    if settings.deployment_tier == "demo":
        simulated_body, _ = simulated_reply_body(
            "This is a simulated Bridge PH support reply for the demo.",
            is_internal=False,
            settings=settings,
        )
        db.add(
            SupportTicketReply(
                ticket_id=ticket.id,
                author_user_id=context.user.id,
                author_role=context.user.role,
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
    deliver_support_ticket_notifications_now(db, ticket, actor=context.user, settings=settings)
    ticket = _load_ticket(ticket.id, context, db)
    return _ticket_response(ticket, admin=_is_admin(context))


@router.get("", response_model=list[SupportTicketResponse])
def list_tickets(
    context: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
    status_filter: SupportTicketStatus | None = Query(default=None, alias="status"),
) -> list[SupportTicketResponse]:
    statement = select(SupportTicket).options(
        selectinload(SupportTicket.requester),
        selectinload(SupportTicket.assigned_to),
        selectinload(SupportTicket.replies).selectinload(SupportTicketReply.author),
    )
    if not _is_admin(context):
        statement = statement.where(SupportTicket.requester_id == context.user.id)
    if status_filter is not None:
        statement = statement.where(SupportTicket.status == status_filter)
    statement = statement.order_by(SupportTicket.created_at.desc())
    tickets = db.scalars(statement).all()
    return [_ticket_response(ticket, admin=_is_admin(context)) for ticket in tickets]


@router.get("/{ticket_id}", response_model=SupportTicketResponse)
def get_ticket(
    ticket_id: str,
    context: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
) -> SupportTicketResponse:
    ticket = _load_ticket(ticket_id, context, db)
    return _ticket_response(ticket, admin=_is_admin(context))


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
    if not _is_admin(context) and settings.deployment_tier != "demo":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    _check_version(ticket, payload.expected_version)
    assignee = None
    if payload.assigned_to_id is not None:
        assignee = db.scalar(
            select(User).where(
                User.id == payload.assigned_to_id,
                User.role == Role.ADMIN,
                User.status == UserStatus.ACTIVE,
            )
        )
        if assignee is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tickets can only be assigned to an active Admin user",
            )
    if ticket.assigned_to_id != payload.assigned_to_id:
        ticket.assigned_to_id = payload.assigned_to_id
        ticket.version += 1
        record_audit(
            db,
            actor_user_id=context.user.id,
            action="SUPPORT_TICKET_ASSIGNED" if assignee else "SUPPORT_TICKET_UNASSIGNED",
            entity_type="support_ticket",
            entity_id=ticket.id,
            correlation_id=getattr(request.state, "correlation_id", None),
            reason=f"{ticket.ticket_number} • {assignee.display_name if assignee else 'Unassigned'}",
        )
        db.commit()
    ticket = _load_ticket(ticket.id, context, db)
    return _ticket_response(ticket, admin=_is_admin(context))


@router.patch("/{ticket_id}/status", response_model=SupportTicketResponse)
def update_ticket_status(
    ticket_id: str,
    payload: SupportTicketStatusUpdate,
    request: Request,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> SupportTicketResponse:
    _require_admin(context)
    ticket = _load_ticket(ticket_id, context, db)
    _set_status(
        ticket,
        payload.status,
        expected_version=payload.expected_version,
        context=context,
        request=request,
        db=db,
    )
    db.commit()
    ticket = _load_ticket(ticket.id, context, db)
    return _ticket_response(ticket, admin=True)


def _action_status(
    ticket_id: str,
    target: SupportTicketStatus,
    payload: SupportTicketAction | None,
    request: Request,
    context: AuthContext,
    db: Session,
) -> SupportTicketResponse:
    _require_admin(context)
    ticket = _load_ticket(ticket_id, context, db)
    _set_status(
        ticket,
        target,
        expected_version=payload.expected_version if payload else None,
        context=context,
        request=request,
        db=db,
    )
    db.commit()
    ticket = _load_ticket(ticket.id, context, db)
    return _ticket_response(ticket, admin=True)


@router.post("/{ticket_id}/reopen", response_model=SupportTicketResponse)
def reopen_ticket(
    ticket_id: str,
    request: Request,
    payload: SupportTicketAction | None = None,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> SupportTicketResponse:
    return _action_status(ticket_id, SupportTicketStatus.OPEN, payload, request, context, db)


@router.post("/{ticket_id}/resolve", response_model=SupportTicketResponse)
def resolve_ticket(
    ticket_id: str,
    request: Request,
    payload: SupportTicketAction | None = None,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> SupportTicketResponse:
    return _action_status(ticket_id, SupportTicketStatus.RESOLVED, payload, request, context, db)


@router.post("/{ticket_id}/close", response_model=SupportTicketResponse)
def close_ticket(
    ticket_id: str,
    request: Request,
    payload: SupportTicketAction | None = None,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> SupportTicketResponse:
    return _action_status(ticket_id, SupportTicketStatus.CLOSED, payload, request, context, db)


@router.post("/{ticket_id}/replies", response_model=SupportTicketResponse)
@router.post("/{ticket_id}/reply", response_model=SupportTicketResponse)
def add_reply(
    ticket_id: str,
    payload: SupportTicketReplyCreate,
    request: Request,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SupportTicketResponse:
    _require_admin(context)
    ticket = _load_ticket(ticket_id, context, db)
    _check_version(ticket, payload.expected_version)
    if ticket.status == SupportTicketStatus.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Reopen the ticket before adding a reply",
        )
    try:
        body, is_simulated = simulated_reply_body(
            payload.body,
            is_internal=payload.is_internal,
            settings=settings,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    reply = SupportTicketReply(
        ticket_id=ticket.id,
        author_user_id=context.user.id,
        author_role=context.user.role,
        body=body,
        is_internal=payload.is_internal,
        is_simulated=is_simulated,
    )
    ticket.version += 1
    db.add(reply)
    db.flush()
    record_audit(
        db,
        actor_user_id=context.user.id,
        action="SUPPORT_TICKET_REPLIED",
        entity_type="support_ticket",
        entity_id=ticket.id,
        correlation_id=getattr(request.state, "correlation_id", None),
        reason=f"{ticket.ticket_number} • {'Internal note' if reply.is_internal else 'Requester-visible reply'}",
    )
    db.commit()
    if not reply.is_internal:
        deliver_support_ticket_notifications_now(
            db,
            ticket,
            actor=context.user,
            settings=settings,
            reply=reply,
        )
    ticket = _load_ticket(ticket.id, context, db)
    return _ticket_response(ticket, admin=True)
