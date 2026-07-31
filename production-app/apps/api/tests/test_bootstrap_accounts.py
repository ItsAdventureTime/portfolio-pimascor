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
                {"username": "carmel.urot", "email": "carmel.urot@pimascor.com", "display_name": "Carmel Urot", "role": "GM"},
                {"username": "dan.c.subido", "email": "dan.c.subido@gmail.com", "display_name": "Dan C. Subido", "role": "DCS"},
                {"username": "leane.tejero", "email": "leane.tejero@pimascor.com", "display_name": "Leane Tejero", "role": "REQUESTER"},
                {"username": "romeo.reano", "email": "romeo.reano@pimascor.com", "display_name": "Romeo Reano", "role": "REQUESTER"},
                {"username": "processor1", "email": "processor1@pimascor", "display_name": "Processor 1", "role": "REQUESTER"},
                {"username": "processor2", "email": "processor2@pimascor.com", "display_name": "Processor 2", "role": "REQUESTER"},
                {"username": "processor3", "email": "processor3@pimascor.com", "display_name": "Processor 3", "role": "REQUESTER"},
                {"username": "operations", "email": "operations@pimascor.com", "display_name": "Mich", "role": "MICH"},
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
