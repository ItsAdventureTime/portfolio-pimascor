import hmac
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_db
from ..dependencies import AuthContext, get_auth_context, require_csrf
from ..models import EmailChallenge, LoginSession, PasswordResetRequest, Role, User, UserStatus, utc_now
from ..schemas import (
    ActivationCompleteRequest,
    ActivationStartRequest,
    AuthenticatedResponse,
    EmailCodeVerifyRequest,
    MeResponse,
    PasswordStartRequest,
    PasswordStartResponse,
    PasswordResetCompleteRequest,
    PasswordResetCompleteResponse,
    PasswordResetStartRequest,
    PasswordResetStartResponse,
    ReleaseUpdateResponse,
    SessionResponse,
)
from ..security import (
    create_csrf_secret,
    create_email_code,
    create_session_secret,
    hash_password,
    hash_secret,
    verify_password,
)
from ..services.audit import record_audit
from ..services.email import get_email_provider
from ..services.release_updates import current_release_update


router = APIRouter(prefix="/auth", tags=["authentication"])

PASSWORD_RESET_MESSAGE = (
    "If that account exists, we will send an email with instructions to reset "
    "the password."
)
PASSWORD_RESET_INVALID = "This password reset link is no longer valid."


def _set_session_cookies(response: Response, settings: Settings, session: LoginSession, raw_session: str, raw_csrf: str) -> None:
    response.set_cookie(
        settings.session_cookie_name,
        f"{session.id}.{raw_session}",
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )
    response.set_cookie(
        settings.csrf_cookie_name,
        raw_csrf,
        httponly=False,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )


def mask_email(email: str) -> str:
    local, domain = email.split("@", 1)
    visible = local[:2] if len(local) > 2 else local[:1]
    return f"{visible}{'*' * max(2, len(local) - len(visible))}@{domain}"


@router.post("/demo", response_model=AuthenticatedResponse)
def demo_session(
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthenticatedResponse:
    """Create the explicitly synthetic Admin session used by the hosted demo."""
    if settings.deployment_tier != "demo":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo sign-in is unavailable")

    user = db.scalar(
        select(User).where(
            User.username == "admin",
            User.role == Role.ADMIN,
            User.status == UserStatus.ACTIVE,
        )
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Demo Admin account is unavailable")

    raw_session = create_session_secret()
    raw_csrf = create_csrf_secret()
    login_session = LoginSession(
        user_id=user.id,
        token_hash=hash_secret(raw_session),
        csrf_hash=hash_secret(raw_csrf),
        expires_at=utc_now() + timedelta(hours=settings.session_ttl_hours),
    )
    db.add(login_session)
    db.flush()
    record_audit(
        db,
        actor_user_id=user.id,
        action="AUTH_DEMO_SESSION_CREATED",
        entity_type="session",
        entity_id=login_session.id,
        correlation_id=getattr(request.state, "correlation_id", None),
        reason="Explicit synthetic demo entry",
    )
    db.commit()
    _set_session_cookies(response, settings, login_session, raw_session, raw_csrf)
    return AuthenticatedResponse(user=MeResponse.model_validate(user), csrf_token=raw_csrf)


@router.post("/password/start", response_model=PasswordStartResponse)
def password_start(
    payload: PasswordStartRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> PasswordStartResponse:
    identifier = payload.username.strip().lower()
    user = db.scalar(
        select(User).where(or_(User.username == identifier, User.email == identifier))
    )
    if (
        user is None
        or user.status != UserStatus.ACTIVE
        or not verify_password(user.password_hash, payload.password)
    ):
        correlation_id = getattr(request.state, "correlation_id", None)
        record_audit(
            db,
            actor_user_id=user.id if user else None,
            action="AUTH_PASSWORD_REJECTED",
            entity_type="authentication",
            entity_id=user.id if user else correlation_id,
            correlation_id=correlation_id,
            reason="Credentials rejected",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if user.password_hash and verify_password(user.password_hash, payload.password):
        # Transparently refresh Argon2 parameters when the library recommendation changes.
        from ..security import password_hasher

        if password_hasher.check_needs_rehash(user.password_hash):
            user.password_hash = hash_password(payload.password)

    code = create_email_code()
    challenge = EmailChallenge(
        user_id=user.id,
        code_hash=hash_password(code),
        expires_at=utc_now() + timedelta(minutes=settings.email_code_ttl_minutes),
    )
    db.add(challenge)
    db.flush()
    record_audit(
        db,
        actor_user_id=user.id,
        action="AUTH_EMAIL_CHALLENGE_CREATED",
        entity_type="email_challenge",
        entity_id=challenge.id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()

    try:
        get_email_provider(settings).send_login_code(
            user.email,
            user.display_name,
            challenge.id,
            code,
            settings.public_app_url,
            settings.email_code_ttl_minutes,
        )
    except Exception as exc:
        challenge.used_at = utc_now()
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The sign-in email could not be sent. Please try again.",
        ) from exc

    return PasswordStartResponse(
        challenge_id=challenge.id,
        destination=mask_email(user.email),
        expires_in_seconds=settings.email_code_ttl_minutes * 60,
        development_code=code if settings.is_development else None,
    )


@router.post("/password-reset/start", response_model=PasswordResetStartResponse)
def password_reset_start(
    payload: PasswordResetStartRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> PasswordResetStartResponse:
    """Create a generic, rate-limited reset request.

    Every request creates a ledger row, including unknown identifiers. Only an
    active, already-activated account receives a one-time link by email.
    """
    identifier = payload.identifier.strip().lower()
    source = request.client.host if request.client else "unknown"
    identifier_hash = hash_secret(identifier)
    source_hash = hash_secret(source or "unknown")
    now = utc_now()
    window_start = now - timedelta(minutes=settings.password_reset_window_minutes)

    identifier_count = db.scalar(
        select(func.count(PasswordResetRequest.id)).where(
            PasswordResetRequest.identifier_hash == identifier_hash,
            PasswordResetRequest.created_at >= window_start,
        )
    ) or 0
    source_count = db.scalar(
        select(func.count(PasswordResetRequest.id)).where(
            PasswordResetRequest.source_hash == source_hash,
            PasswordResetRequest.created_at >= window_start,
        )
    ) or 0
    limited = (
        identifier_count >= settings.password_reset_identifier_limit
        or source_count >= settings.password_reset_source_limit
    )
    user = db.scalar(
        select(User).where(or_(User.username == identifier, User.email == identifier))
    )
    eligible_user = (
        user is not None
        and user.status == UserStatus.ACTIVE
        and not user.must_set_password
    )
    token = create_session_secret() if eligible_user and not limited else None
    reset_request = PasswordResetRequest(
        user_id=user.id if eligible_user else None,
        identifier_hash=identifier_hash,
        source_hash=source_hash,
        token_hash=hash_secret(token) if token else None,
        expires_at=now + timedelta(minutes=settings.password_reset_ttl_minutes),
    )
    db.add(reset_request)
    db.flush()
    record_audit(
        db,
        actor_user_id=user.id if eligible_user else None,
        action="AUTH_PASSWORD_RESET_REQUESTED",
        entity_type="password_reset_request",
        entity_id=reset_request.id,
        correlation_id=getattr(request.state, "correlation_id", None),
        reason="Rate limited" if limited else None,
    )
    db.commit()

    if token and user is not None:
        try:
            get_email_provider(settings).send_password_reset(
                user.email,
                user.display_name,
                reset_request.id,
                token,
                settings.public_app_url,
                settings.password_reset_ttl_minutes,
            )
        except Exception:
            reset_request.used_at = utc_now()
            record_audit(
                db,
                actor_user_id=user.id,
                action="AUTH_PASSWORD_RESET_EMAIL_FAILED",
                entity_type="password_reset_request",
                entity_id=reset_request.id,
                correlation_id=getattr(request.state, "correlation_id", None),
                reason="Email provider rejected the reset message",
            )
            db.commit()
            # Preserve the non-disclosing response even when the provider is
            # unavailable. The audit event gives operators a safe failure
            # signal without turning account existence into a status oracle.

    return PasswordResetStartResponse(
        message=PASSWORD_RESET_MESSAGE,
        expires_in_seconds=settings.password_reset_ttl_minutes * 60,
        development_code=token if token and settings.is_development else None,
        development_challenge_id=reset_request.id if token and settings.is_development else None,
    )


@router.post("/password-reset/complete", response_model=PasswordResetCompleteResponse)
def password_reset_complete(
    payload: PasswordResetCompleteRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> PasswordResetCompleteResponse:
    challenge = db.scalar(
        select(PasswordResetRequest)
        .where(PasswordResetRequest.id == payload.challenge_id)
        .with_for_update()
    )
    now = utc_now()
    if challenge is None or challenge.used_at is not None or challenge.token_hash is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=PASSWORD_RESET_INVALID)

    expires_at = challenge.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=now.tzinfo)
    if expires_at <= now or challenge.attempts >= 5:
        challenge.used_at = now
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=PASSWORD_RESET_INVALID)

    challenge.attempts += 1
    token_hash = hash_secret(payload.token)
    if not hmac.compare_digest(challenge.token_hash, token_hash):
        if challenge.attempts >= 5:
            challenge.used_at = now
        record_audit(
            db,
            actor_user_id=challenge.user_id,
            action="AUTH_PASSWORD_RESET_REJECTED",
            entity_type="password_reset_request",
            entity_id=challenge.id,
            correlation_id=getattr(request.state, "correlation_id", None),
            reason="Incorrect or expired reset token",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=PASSWORD_RESET_INVALID)

    user = db.get(User, challenge.user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        challenge.used_at = now
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=PASSWORD_RESET_INVALID)

    user.password_hash = hash_password(payload.password)
    user.must_set_password = False
    user.email_verified_at = user.email_verified_at or now
    challenge.used_at = now
    db.execute(
        update(LoginSession)
        .where(LoginSession.user_id == user.id, LoginSession.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    db.execute(
        update(EmailChallenge)
        .where(EmailChallenge.user_id == user.id, EmailChallenge.used_at.is_(None))
        .values(used_at=now)
    )
    record_audit(
        db,
        actor_user_id=user.id,
        action="AUTH_PASSWORD_RESET_COMPLETED",
        entity_type="user",
        entity_id=user.id,
        correlation_id=getattr(request.state, "correlation_id", None),
        reason="All existing sessions revoked",
    )
    db.commit()
    return PasswordResetCompleteResponse(
        message="Your password has been reset. Sign in again with the new password."
    )


@router.get("/release-updates", response_model=ReleaseUpdateResponse | None)
def release_updates(
    context: AuthContext = Depends(get_auth_context),
) -> ReleaseUpdateResponse | None:
    current = current_release_update()
    return current if context.user.last_seen_release_id != current.id else None


@router.post("/release-updates/ack", status_code=status.HTTP_204_NO_CONTENT)
def acknowledge_release_update(
    request: Request,
    response: Response,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> Response:
    current = current_release_update()
    if context.user.last_seen_release_id != current.id:
        context.user.last_seen_release_id = current.id
        record_audit(
            db,
            actor_user_id=context.user.id,
            action="AUTH_RELEASE_UPDATE_ACKNOWLEDGED",
            entity_type="release_update",
            entity_id=current.id,
            correlation_id=getattr(request.state, "correlation_id", None),
            reason="User viewed the latest product update",
        )
        db.commit()
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post("/activation/start", response_model=PasswordStartResponse)
def activation_start(
    payload: ActivationStartRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> PasswordStartResponse:
    identifier = payload.username.strip().lower()
    user = db.scalar(
        select(User).where(or_(User.username == identifier, User.email == identifier))
    )
    if user is None or user.status != UserStatus.ACTIVE or not user.must_set_password:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account activation is not available")

    code = create_email_code()
    challenge = EmailChallenge(
        user_id=user.id,
        purpose="ACTIVATION",
        code_hash=hash_password(code),
        expires_at=utc_now() + timedelta(minutes=settings.email_code_ttl_minutes),
    )
    db.add(challenge)
    db.flush()
    record_audit(
        db,
        actor_user_id=user.id,
        action="AUTH_ACTIVATION_CHALLENGE_CREATED",
        entity_type="email_challenge",
        entity_id=challenge.id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()

    try:
        get_email_provider(settings).send_activation_code(
            user.email,
            user.display_name,
            challenge.id,
            code,
            settings.public_app_url,
            settings.email_code_ttl_minutes,
        )
    except Exception as exc:
        challenge.used_at = utc_now()
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The activation email could not be sent. Please try again.",
        ) from exc

    return PasswordStartResponse(
        challenge_id=challenge.id,
        destination=mask_email(user.email),
        expires_in_seconds=settings.email_code_ttl_minutes * 60,
        development_code=code if settings.is_development else None,
    )


@router.post("/activation/complete", response_model=AuthenticatedResponse)
def activation_complete(
    payload: ActivationCompleteRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthenticatedResponse:
    challenge = db.get(EmailChallenge, payload.challenge_id)
    if challenge is None or challenge.purpose != "ACTIVATION" or challenge.used_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Activation code is no longer valid")
    challenge.attempts += 1
    expires_at = challenge.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=utc_now().tzinfo)
    if expires_at <= utc_now() or challenge.attempts > 5:
        challenge.used_at = utc_now()
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Activation code is no longer valid")
    if not verify_password(challenge.code_hash, payload.code):
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect activation code")

    user = db.get(User, challenge.user_id)
    if user is None or user.status != UserStatus.ACTIVE or not user.must_set_password:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account activation is not available")

    user.password_hash = hash_password(payload.password)
    user.must_set_password = False
    user.email_verified_at = user.email_verified_at or utc_now()
    challenge.used_at = utc_now()
    raw_session = create_session_secret()
    raw_csrf = create_csrf_secret()
    login_session = LoginSession(
        user_id=user.id,
        token_hash=hash_secret(raw_session),
        csrf_hash=hash_secret(raw_csrf),
        expires_at=utc_now() + timedelta(hours=settings.session_ttl_hours),
    )
    db.add(login_session)
    db.flush()
    record_audit(
        db,
        actor_user_id=user.id,
        action="AUTH_ACCOUNT_ACTIVATED",
        entity_type="user",
        entity_id=user.id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    _set_session_cookies(response, settings, login_session, raw_session, raw_csrf)
    return AuthenticatedResponse(user=MeResponse.model_validate(user), csrf_token=raw_csrf)


@router.post("/email-code/verify", response_model=AuthenticatedResponse)
def verify_email_code(
    payload: EmailCodeVerifyRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthenticatedResponse:
    challenge = db.get(EmailChallenge, payload.challenge_id)
    if challenge is None or challenge.purpose != "LOGIN" or challenge.used_at is not None:
        correlation_id = getattr(request.state, "correlation_id", None)
        record_audit(
            db,
            actor_user_id=challenge.user_id if challenge else None,
            action="AUTH_EMAIL_CODE_REJECTED",
            entity_type="email_challenge",
            entity_id=challenge.id if challenge else correlation_id,
            correlation_id=correlation_id,
            reason="Challenge is no longer valid",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Code is no longer valid")
    challenge.attempts += 1
    expires_at = challenge.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=utc_now().tzinfo)
    if expires_at <= utc_now() or challenge.attempts > 5:
        challenge.used_at = utc_now()
        record_audit(
            db,
            actor_user_id=challenge.user_id,
            action="AUTH_EMAIL_CODE_REJECTED",
            entity_type="email_challenge",
            entity_id=challenge.id,
            correlation_id=getattr(request.state, "correlation_id", None),
            reason="Challenge expired or attempt limit reached",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Code is no longer valid")
    if not verify_password(challenge.code_hash, payload.code):
        record_audit(
            db,
            actor_user_id=challenge.user_id,
            action="AUTH_EMAIL_CODE_REJECTED",
            entity_type="email_challenge",
            entity_id=challenge.id,
            correlation_id=getattr(request.state, "correlation_id", None),
            reason="Incorrect verification code",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect code")

    user = db.get(User, challenge.user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is not active")

    challenge.used_at = utc_now()
    user.email_verified_at = user.email_verified_at or utc_now()
    raw_session = create_session_secret()
    raw_csrf = create_csrf_secret()
    login_session = LoginSession(
        user_id=user.id,
        token_hash=hash_secret(raw_session),
        csrf_hash=hash_secret(raw_csrf),
        expires_at=utc_now() + timedelta(hours=settings.session_ttl_hours),
    )
    db.add(login_session)
    db.flush()
    record_audit(
        db,
        actor_user_id=user.id,
        action="AUTH_LOGIN_SUCCEEDED",
        entity_type="session",
        entity_id=login_session.id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()

    _set_session_cookies(response, settings, login_session, raw_session, raw_csrf)
    return AuthenticatedResponse(user=MeResponse.model_validate(user), csrf_token=raw_csrf)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    request: Request,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    context.session.revoked_at = utc_now()
    record_audit(
        db,
        actor_user_id=context.user.id,
        action="AUTH_LOGOUT",
        entity_type="session",
        entity_id=context.session.id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    response.status_code = status.HTTP_204_NO_CONTENT
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.delete_cookie(settings.csrf_cookie_name, path="/")
    return response


@router.get("/me", response_model=MeResponse)
def me(context: AuthContext = Depends(get_auth_context)) -> MeResponse:
    return MeResponse.model_validate(context.user)


@router.get("/me/sessions", response_model=list[SessionResponse])
def sessions(
    context: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)
) -> list[SessionResponse]:
    rows = db.scalars(
        select(LoginSession)
        .where(LoginSession.user_id == context.user.id, LoginSession.revoked_at.is_(None))
        .order_by(LoginSession.created_at.desc())
    ).all()
    return [
        SessionResponse(
            id=row.id,
            created_at=row.created_at,
            last_seen_at=row.last_seen_at,
            expires_at=row.expires_at,
            current=row.id == context.session.id,
        )
        for row in rows
    ]


@router.delete("/me/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_session(
    session_id: str,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> Response:
    login_session = db.scalar(
        select(LoginSession).where(
            LoginSession.id == session_id,
            LoginSession.user_id == context.user.id,
            LoginSession.revoked_at.is_(None),
        )
    )
    if login_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    login_session.revoked_at = utc_now()
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
