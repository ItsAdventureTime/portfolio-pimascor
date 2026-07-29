import sys

from sqlalchemy import select

from pimascor_api import account_admin
from pimascor_api.models import LoginSession, User, UserStatus
from pimascor_api.security import verify_password

from .conftest import TestingSession


def test_account_admin_changes_password_and_disables_user(monkeypatch, capsys):
    monkeypatch.setattr(account_admin, "SessionLocal", TestingSession)
    with TestingSession() as db:
        user = db.scalar(select(User).where(User.username == "requester"))
        assert user is not None
        username = user.username

    monkeypatch.setattr(sys, "argv", ["account-admin", "set-password", username])
    monkeypatch.setattr(account_admin.getpass, "getpass", lambda _: "Replacement-2026!")
    account_admin.main()

    with TestingSession() as db:
        updated = db.scalar(select(User).where(User.username == username))
        assert updated is not None
        assert verify_password(updated.password_hash, "Replacement-2026!")

    monkeypatch.setattr(sys, "argv", ["account-admin", "disable", username])
    account_admin.main()

    with TestingSession() as db:
        disabled = db.scalar(select(User).where(User.username == username))
        assert disabled is not None
        assert disabled.status == UserStatus.DISABLED
        assert db.scalars(
            select(LoginSession).where(
                LoginSession.user_id == disabled.id,
                LoginSession.revoked_at.is_(None),
            )
        ).all() == []

    assert "Password updated" in capsys.readouterr().out
