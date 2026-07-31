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
                {
                    "username": "new-gm",
                    "email": "new-gm@example.com",
                    "display_name": "New GM",
                    "role": "GM",
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(bootstrap_accounts, "SessionLocal", TestingSession)
    monkeypatch.setattr(sys, "argv", ["bootstrap-accounts", "--manifest", str(manifest)])
    bootstrap_accounts.main()
    bootstrap_accounts.main()

    with TestingSession() as db:
        user = db.query(User).filter(User.username == "new-gm").one()
        assert user.role == Role.GM
        assert user.must_set_password is True
        assert user.password_hash
