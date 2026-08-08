import json
import sys

from .conftest import TestingSession
from pimascor_api import bootstrap_accounts
from pimascor_api.models import Role, User


def test_bootstrap_accounts_creates_pending_role_accounts_and_is_idempotent(tmp_path, monkeypatch):
    manifest = tmp_path / "accounts.json"
    manifest.write_text(
        json.dumps(
            [
                {"username": "admin-team", "email": "team@bridge-ph.com", "display_name": "Bridge PH Team", "role": "ADMIN"},
                {"username": "alyssa.d", "email": "alyssa.d@bridge-ph.com", "display_name": "Alyssa D.", "role": "ADMIN"},
                {"username": "carmel.urot", "email": "carmel.urot@gmail.com", "display_name": "Carmel C. Urot", "role": "GM"},
                {"username": "dan.c.subido", "email": "dan.c.subido@gmail.com", "display_name": "Atty. Daniel C. Subido", "role": "DCS"},
                {"username": "leane.tejero", "email": "leane.tejero@pimascor.com", "display_name": "Leane Tejero", "role": "REQUESTER"},
                {"username": "romeo.reano", "email": "romeo.reano@pimascor.com", "display_name": "Romeo Reano", "role": "REQUESTER"},
                {"username": "processor1", "email": "processor1@pimascor.com", "display_name": "Marcelo Sabando", "role": "REQUESTER"},
                {"username": "processor2", "email": "processor2@pimascor.com", "display_name": "Christian Arcangel", "role": "REQUESTER"},
                {"username": "processor3", "email": "processor3@pimascor.com", "display_name": "Jaycee Dimandal", "role": "REQUESTER"},
                {"username": "operations", "email": "operations@pimascor.com", "display_name": "Michelle Umpacuman", "role": "MICH"},
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(bootstrap_accounts, "SessionLocal", TestingSession)
    monkeypatch.setattr(sys, "argv", ["bootstrap-accounts", "--manifest", str(manifest)])
    bootstrap_accounts.main()
    bootstrap_accounts.main()

    with TestingSession() as db:
        users = db.query(User).filter(User.username.in_((
            "admin-team", "alyssa.d", "carmel.urot", "dan.c.subido", "leane.tejero",
            "romeo.reano", "processor1", "processor2", "processor3", "operations",
        ))).all()
        assert len(users) == 10
        assert {user.role for user in users} == {Role.ADMIN, Role.GM, Role.DCS, Role.REQUESTER, Role.MICH}
        assert all(user.must_set_password is True and user.password_hash for user in users)


def test_bootstrap_rejects_invalid_processor_email(tmp_path, monkeypatch):
    manifest = tmp_path / "accounts.json"
    manifest.write_text(
        json.dumps([{"username": "processor1", "email": "processor1@pimascor", "display_name": "Marcelo Sabando", "role": "REQUESTER"}]),
        encoding="utf-8",
    )
    monkeypatch.setattr(bootstrap_accounts, "SessionLocal", TestingSession)
    monkeypatch.setattr(sys, "argv", ["bootstrap-accounts", "--manifest", str(manifest)])
    try:
        bootstrap_accounts.main()
    except SystemExit as exc:
        assert "deliverable domain" in str(exc)
    else:
        raise AssertionError("Incomplete email domain was accepted")


def test_bootstrap_updates_pending_account_metadata(tmp_path, monkeypatch):
    manifest = tmp_path / "accounts.json"
    manifest.write_text(
        json.dumps([{"username": "carmel.urot", "email": "carmel.urot@gmail.com", "display_name": "Carmel C. Urot", "role": "GM"}]),
        encoding="utf-8",
    )
    with TestingSession() as db:
        db.add(User(
            username="carmel.urot",
            email="old@example.com",
            display_name="Old Name",
            password_hash="old-hash",
            must_set_password=True,
            role=Role.REQUESTER,
        ))
        db.commit()
    monkeypatch.setattr(bootstrap_accounts, "SessionLocal", TestingSession)
    monkeypatch.setattr(sys, "argv", ["bootstrap-accounts", "--manifest", str(manifest)])
    bootstrap_accounts.main()
    with TestingSession() as db:
        user = db.query(User).filter(User.username == "carmel.urot").one()
        assert user.email == "carmel.urot@gmail.com"
        assert user.display_name == "Carmel C. Urot"
        assert user.role == Role.GM
        assert user.must_set_password is True
