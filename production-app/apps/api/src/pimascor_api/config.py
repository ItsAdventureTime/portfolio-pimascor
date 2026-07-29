from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    app_env: Literal["development", "test", "maintenance", "production"] = "development"
    deployment_tier: Literal["development", "test", "demo", "production"] = "development"
    app_name: str = "PIMASCOR API"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./var/pimascor.db"
    database_url_file: Path | None = None
    frontend_origins: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]
    public_app_url: str = "http://127.0.0.1:5173/"

    session_cookie_name: str = "pimascor_session"
    csrf_cookie_name: str = "pimascor_csrf"
    session_cookie_secure: bool = False
    session_ttl_hours: int = 12
    email_code_ttl_minutes: int = 5
    email_provider: Literal["development", "resend", "azure"] = "development"
    resend_api_key_file: Path | None = None
    email_from_address: str = "PIMASCOR <no-reply@example.com>"
    azure_email_endpoint: str | None = None
    azure_email_access_key_file: Path | None = None
    incident_email_enabled: bool = True
    incident_admin_email: str = "alyssa.d@bridge-ph.com"
    incident_developer_email: str = "jk@delegateops.business"

    b2_endpoint_url: str | None = None
    b2_region: str | None = None
    b2_bucket: str | None = None
    b2_object_prefix: str | None = None
    b2_key_id_file: Path | None = None
    b2_application_key_file: Path | None = None
    pdf_preview_retention_hours: int = 12

    @model_validator(mode="after")
    def validate_runtime_security(self) -> "Settings":
        if self.database_url_file:
            self.database_url = self.read_secret(self.database_url_file, "database URL")
        if self.app_env in ("maintenance", "production"):
            if self.database_url_file is None:
                raise ValueError(
                    "DATABASE_URL_FILE must reference a Podman secret in maintenance or production"
                )
            b2_values = (
                self.b2_endpoint_url,
                self.b2_region,
                self.b2_bucket,
                self.b2_object_prefix,
                self.b2_key_id_file,
                self.b2_application_key_file,
            )
            if any(b2_values) and not all(b2_values):
                raise ValueError(
                    "Backblaze endpoint, region, bucket, object prefix, and both Podman secret files must be configured together"
                )
        if self.app_env == "production":
            if not self.public_app_url.startswith("https://"):
                raise ValueError("PUBLIC_APP_URL must use HTTPS in production")
            if self.email_provider == "development":
                raise ValueError("EMAIL_PROVIDER cannot be development in production")
            if self.email_provider == "resend" and self.resend_api_key_file is None:
                raise ValueError("RESEND_API_KEY_FILE must reference a Podman secret")
            if self.email_provider == "azure" and self.azure_email_access_key_file is None:
                raise ValueError("AZURE_EMAIL_ACCESS_KEY_FILE must reference a Podman secret")
            if not self.session_cookie_secure:
                raise ValueError("SESSION_COOKIE_SECURE must be true in production")
        return self

    @staticmethod
    def read_secret(path: Path | None, label: str) -> str:
        if path is None:
            raise RuntimeError(f"A Podman secret file is required for {label}")
        try:
            value = path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise RuntimeError(f"Could not read the Podman secret file for {label}") from exc
        if not value:
            raise RuntimeError(f"The Podman secret file for {label} is empty")
        return value

    @property
    def resend_api_key_value(self) -> str:
        return self.read_secret(self.resend_api_key_file, "Resend API key")

    @property
    def azure_email_access_key_value(self) -> str:
        return self.read_secret(self.azure_email_access_key_file, "Azure email access key")

    @property
    def b2_key_id_value(self) -> str:
        return self.read_secret(self.b2_key_id_file, "Backblaze key ID")

    @property
    def b2_application_key_value(self) -> str:
        return self.read_secret(self.b2_application_key_file, "Backblaze application key")

    @property
    def is_development(self) -> bool:
        return self.app_env in ("development", "test")

    def ensure_local_paths(self) -> None:
        if self.database_url.startswith("sqlite"):
            path_part = self.database_url.rsplit("///", 1)[-1]
            if path_part != ":memory:":
                Path(path_part).parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
