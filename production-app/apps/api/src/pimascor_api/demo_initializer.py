"""Create the synthetic accounts required by the hosted demo."""

from __future__ import annotations

import secrets

from sqlalchemy import select

from .config import get_settings
from .db import Base, SessionLocal, engine
from .models import Role, User, UserStatus, utc_now
from .security import hash_password


DEMO_ACCOUNTS = (
    ("admin", "admin@demo.delegateops.business", "Demo Administrator", Role.ADMIN),
    ("requester", "requester@demo.delegateops.business", "Demo Requester", Role.REQUESTER),
    ("gm", "gm@demo.delegateops.business", "Demo General Manager", Role.GM),
    ("dcs", "dcs@demo.delegateops.business", "Demo DCS", Role.DCS),
    ("mich", "mich@demo.delegateops.business", "Demo MICH", Role.MICH),
)


def ensure_demo_accounts() -> None:
    if get_settings().deployment_tier != "demo":
        raise SystemExit("Refusing to initialize demo accounts outside the demo tier.")

    Base.metadata.create_all(bind=engine)
    with SessionLocal.begin() as db:
        for username, email, display_name, role in DEMO_ACCOUNTS:
            user = db.scalar(select(User).where(User.username == username))
            if user is None:
                db.add(
                    User(
                        username=username,
                        email=email,
                        display_name=display_name,
                        password_hash=hash_password(secrets.token_urlsafe(48)),
                        role=role,
                        status=UserStatus.ACTIVE,
                        email_verified_at=utc_now(),
                    )
                )
                continue

            # Keep a manually seeded demo database usable while preserving its
            # password hash; demo entry is through the server-side session.
            user.email = email
            user.display_name = display_name
            user.role = role
            user.status = UserStatus.ACTIVE
            user.must_set_password = False
            user.email_verified_at = user.email_verified_at or utc_now()


if __name__ == "__main__":
    ensure_demo_accounts()
