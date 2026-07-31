import hmac
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import Settings, get_settings
from .db import get_db
from .models import LoginSession, Role, User, UserStatus, utc_now
from .security import hash_secret


@dataclass
class AuthContext:
    user: User
    session: LoginSession


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def get_auth_context(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthContext:
    session_cookie = request.cookies.get(settings.session_cookie_name)
    if not session_cookie or "." not in session_cookie:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in is required")

    session_id, raw_secret = session_cookie.split(".", 1)
    login_session = db.scalar(select(LoginSession).where(LoginSession.id == session_id))
    if (
        login_session is None
        or login_session.revoked_at is not None
        or _as_utc(login_session.expires_at) <= utc_now()
        or not hmac.compare_digest(login_session.token_hash, hash_secret(raw_secret))
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    user = db.get(User, login_session.user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is not active")

    login_session.last_seen_at = utc_now()
    db.commit()
    return AuthContext(user=user, session=login_session)


def require_csrf(
    request: Request,
    context: AuthContext = Depends(get_auth_context),
    csrf_header: str | None = Header(default=None, alias="X-CSRF-Token"),
    settings: Settings = Depends(get_settings),
) -> AuthContext:
    csrf_cookie = request.cookies.get(settings.csrf_cookie_name)
    if (
        not csrf_header
        or not csrf_cookie
        or not hmac.compare_digest(csrf_header, csrf_cookie)
        or not hmac.compare_digest(context.session.csrf_hash, hash_secret(csrf_header))
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")
    return context


def _role_is_allowed(user_role: Role, roles: tuple[Role, ...], settings: Settings) -> bool:
    if user_role == Role.ADMIN or user_role in roles:
        return True
    if settings.deployment_tier != "production":
        return False
    # Production Users & Roles policy: GM is the operational superuser but not
    # the Administrator; DCS may override any GM-owned approval endpoint.
    if user_role == Role.GM and Role.ADMIN not in roles:
        return True
    if user_role == Role.DCS and Role.GM in roles:
        return True
    return False


def roles_allowed(*roles: Role):
    def dependency(
        context: AuthContext = Depends(get_auth_context),
        settings: Settings = Depends(get_settings),
    ) -> AuthContext:
        # Administrator is the explicit application superuser. It inherits every
        # protected role capability while remaining attributable as ADMIN in
        # audit records; endpoint state and validation rules still apply.
        if not _role_is_allowed(context.user.role, roles, settings):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
        return context

    return dependency


def csrf_roles_allowed(*roles: Role):
    def dependency(
        context: AuthContext = Depends(require_csrf),
        settings: Settings = Depends(get_settings),
    ) -> AuthContext:
        if not _role_is_allowed(context.user.role, roles, settings):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
        return context

    return dependency
