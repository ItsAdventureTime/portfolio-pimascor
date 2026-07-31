"""Create idempotent production accounts awaiting email activation.

The manifest contains account metadata only. It is normally mounted from a
rootless Podman secret; no initial password is accepted or persisted.
"""

from __future__ import annotations

import argparse
import json
import re
import secrets
from pathlib import Path

from sqlalchemy import select

from .db import SessionLocal
from .models import Role, User, UserStatus
from .security import hash_password


USERNAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{1,79}$")


def load_manifest(path: Path) -> list[dict[str, str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Invalid account manifest: {exc}") from exc
    if not isinstance(payload, list) or not payload:
        raise SystemExit("Account manifest must be a non-empty JSON array")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap production accounts awaiting email activation")
    parser.add_argument(
        "--manifest",
        default="/run/secrets/bridge_ph_pimascor_account_bootstrap",
        type=Path,
    )
    args = parser.parse_args()
    manifest = load_manifest(args.manifest)
    seen_usernames: set[str] = set()
    seen_emails: set[str] = set()

    with SessionLocal() as db:
        for index, entry in enumerate(manifest, start=1):
            if not isinstance(entry, dict):
                raise SystemExit(f"Manifest entry {index} must be an object")
            try:
                username = str(entry["username"]).strip().lower()
                email = str(entry["email"]).strip().lower()
                display_name = str(entry["display_name"]).strip()
                role = Role(str(entry["role"]).strip().upper())
            except (KeyError, ValueError) as exc:
                raise SystemExit(f"Invalid manifest entry {index}: {exc}") from exc
            if not USERNAME_PATTERN.fullmatch(username):
                raise SystemExit(f"Invalid username in manifest entry {index}")
            if "@" not in email or len(email) > 320:
                raise SystemExit(f"Invalid email in manifest entry {index}")
            if not display_name or len(display_name) > 160:
                raise SystemExit(f"Invalid display name in manifest entry {index}")
            if username in seen_usernames or email in seen_emails:
                raise SystemExit(f"Duplicate account in manifest entry {index}")
            seen_usernames.add(username)
            seen_emails.add(email)

            user = db.scalar(select(User).where(User.username == username))
            by_email = db.scalar(select(User).where(User.email == email))
            if user is None and by_email is not None:
                raise SystemExit(f"Email is already assigned to another account: {email}")
            if user is not None:
                if user.email != email or user.role != role:
                    raise SystemExit(f"Existing account metadata differs: {username}")
                print(f"Keeping existing account {username} ({role.value})")
                continue

            user = User(
                username=username,
                email=email,
                display_name=display_name,
                password_hash=hash_password(secrets.token_urlsafe(48)),
                must_set_password=True,
                role=role,
                status=UserStatus.ACTIVE,
            )
            db.add(user)
            print(f"Created pending activation account {username} ({role.value})")
        db.commit()


if __name__ == "__main__":
    main()
