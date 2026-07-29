import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError


password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def create_session_secret() -> str:
    return secrets.token_urlsafe(48)


def create_csrf_secret() -> str:
    return secrets.token_urlsafe(32)


def create_email_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"
