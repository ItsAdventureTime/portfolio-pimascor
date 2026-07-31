import argparse
import getpass

from sqlalchemy import select

from .db import SessionLocal
from .models import LoginSession, User, UserStatus, utc_now
from .security import hash_password
from .services.audit import record_audit


def get_user(db, username: str) -> User:
    user = db.scalar(select(User).where(User.username == username.strip().lower()))
    if user is None:
        raise SystemExit(f"User {username!r} does not exist")
    return user


def prompt_password() -> str:
    password = getpass.getpass("New password (12+ characters): ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match")
    if len(password) < 12:
        raise SystemExit("Password must contain at least 12 characters")
    return password


def revoke_sessions(db, user_id: str) -> int:
    sessions = db.scalars(
        select(LoginSession).where(
            LoginSession.user_id == user_id,
            LoginSession.revoked_at.is_(None),
        )
    ).all()
    for session in sessions:
        session.revoked_at = utc_now()
    return len(sessions)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Safely administer PIMASCOR accounts without deleting audit history"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list", help="List accounts without password data")

    password_parser = subparsers.add_parser("set-password", help="Set a password and revoke sessions")
    password_parser.add_argument("username")

    for command in ("disable", "enable"):
        status_parser = subparsers.add_parser(command, help=f"{command.title()} an account")
        status_parser.add_argument("username")

    args = parser.parse_args()

    with SessionLocal() as db:
        if args.command == "list":
            users = db.scalars(select(User).order_by(User.role, User.username)).all()
            print(f"{'USERNAME':<22} {'ROLE':<12} {'STATUS':<12} EMAIL")
            for user in users:
                print(f"{user.username:<22} {user.role.value:<12} {user.status.value:<12} {user.email}")
            return

        user = get_user(db, args.username)
        if args.command == "set-password":
            user.password_hash = hash_password(prompt_password())
            revoked = revoke_sessions(db, user.id)
            record_audit(
                db,
                actor_user_id=None,
                action="CLI_USER_PASSWORD_CHANGED",
                entity_type="user",
                entity_id=user.id,
                reason=f"Rootless operator CLI; revoked {revoked} session(s)",
            )
            db.commit()
            print(f"Password updated for {user.username!r}; revoked {revoked} active session(s).")
            return

        target_status = UserStatus.DISABLED if args.command == "disable" else UserStatus.ACTIVE
        user.status = target_status
        revoked = revoke_sessions(db, user.id) if target_status == UserStatus.DISABLED else 0
        record_audit(
            db,
            actor_user_id=None,
            action=f"CLI_USER_{target_status.value}",
            entity_type="user",
            entity_id=user.id,
            reason=f"Rootless operator CLI; revoked {revoked} session(s)",
        )
        db.commit()
        print(
            f"Account {user.username!r} is now {target_status.value}; "
            f"revoked {revoked} active session(s)."
        )


if __name__ == "__main__":
    main()
