import argparse
import getpass

from sqlalchemy import select

from .db import Base, SessionLocal, engine
from .models import Client, Role, User
from .security import hash_password


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a PIMASCOR account")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--email", default="admin@example.com")
    parser.add_argument("--display-name", default="PIMASCOR Administrator")
    parser.add_argument(
        "--role",
        type=str.upper,
        choices=[role.value for role in Role],
        default=Role.ADMIN.value,
        help="Permission role for the new account",
    )
    args = parser.parse_args()

    password = getpass.getpass("Initial account password (12+ characters): ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match")
    if len(password) < 12:
        raise SystemExit("Password must contain at least 12 characters")

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.username == args.username.lower())):
            raise SystemExit(f"User {args.username!r} already exists")
        user = User(
            username=args.username.lower(),
            email=args.email.lower(),
            display_name=args.display_name,
            password_hash=hash_password(password),
            role=Role(args.role),
        )
        db.add(user)
        for code, name in (("DEMO", "Demo Client"), ("WALKIN", "Walk-in Client")):
            if not db.scalar(select(Client).where(Client.code == code)):
                db.add(Client(code=code, name=name))
        db.commit()
    print(f"Created {args.role} account {args.username!r} and local reference clients.")


if __name__ == "__main__":
    main()
