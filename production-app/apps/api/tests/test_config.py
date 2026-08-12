import pytest
from pydantic import ValidationError

from pimascor_api.config import Settings
from pimascor_api.dependencies import _role_is_allowed
from pimascor_api.models import Role


def test_maintenance_runtime_requires_database_secret():
    with pytest.raises(ValidationError, match="DATABASE_URL_FILE must reference a Podman secret"):
        Settings(app_env="maintenance", deployment_tier="demo", database_url_file=None)


def test_maintenance_runtime_does_not_require_api_only_secrets(tmp_path):
    database_secret = tmp_path / "database_url"
    database_secret.write_text("postgresql+psycopg://demo:secret@database/demo", encoding="utf-8")

    settings = Settings(
        app_env="maintenance",
        deployment_tier="demo",
        database_url_file=database_secret,
    )

    assert settings.database_url == "postgresql+psycopg://demo:secret@database/demo"
    assert settings.email_provider == "development"
    assert settings.session_cookie_secure is False


def test_backblaze_configuration_is_all_or_nothing(tmp_path):
    database_secret = tmp_path / "database_url"
    database_secret.write_text("postgresql+psycopg://demo:secret@database/demo", encoding="utf-8")

    with pytest.raises(ValidationError, match="Backblaze endpoint, region, bucket"):
        Settings(
            app_env="maintenance",
            deployment_tier="demo",
            database_url_file=database_secret,
            b2_endpoint_url="https://s3.us-west-001.backblazeb2.com",
        )


def test_production_backblaze_storage_uses_canonical_bucket_and_prefix(tmp_path):
    database_secret = tmp_path / "database_url"
    database_secret.write_text("postgresql+psycopg://demo:secret@database/demo", encoding="utf-8")
    resend_secret = tmp_path / "resend"
    resend_secret.write_text("test-resend-key", encoding="utf-8")
    key_id = tmp_path / "key-id"
    key_id.write_text("test-key-id", encoding="utf-8")
    application_key = tmp_path / "application-key"
    application_key.write_text("test-application-key", encoding="utf-8")

    with pytest.raises(ValidationError, match="bucket bridge-ph and object prefix pimascor"):
        Settings(
            app_env="production",
            deployment_tier="production",
            database_url_file=database_secret,
            public_app_url="https://delegateops.business/pimascor/",
            email_provider="resend",
            resend_api_key_file=resend_secret,
            session_cookie_secure=True,
            b2_endpoint_url="https://s3.us-west-001.backblazeb2.com",
            b2_region="us-west-001",
            b2_bucket="bridge-ph",
            b2_object_prefix="pimascor/production",
            b2_key_id_file=key_id,
            b2_application_key_file=application_key,
        )


def test_demo_backblaze_storage_uses_canonical_bucket_and_prefix(tmp_path):
    database_secret = tmp_path / "database_url"
    database_secret.write_text("postgresql+psycopg://demo:secret@database/demo", encoding="utf-8")
    key_id = tmp_path / "key-id"
    key_id.write_text("test-key-id", encoding="utf-8")
    application_key = tmp_path / "application-key"
    application_key.write_text("test-application-key", encoding="utf-8")

    with pytest.raises(ValidationError, match="Demo Backblaze storage must use bucket bridge-ph and object prefix pimascor/demo"):
        Settings(
            app_env="maintenance",
            deployment_tier="demo",
            database_url_file=database_secret,
            b2_endpoint_url="https://s3.us-west-001.backblazeb2.com",
            b2_region="us-west-001",
            b2_bucket="bridge-ph",
            b2_object_prefix="pimascor",
            b2_key_id_file=key_id,
            b2_application_key_file=application_key,
        )


def test_production_users_and_roles_escalation_is_isolated_to_production():
    production = Settings(deployment_tier="production")
    test = Settings(deployment_tier="test")

    assert _role_is_allowed(Role.GM, (Role.MICH,), production)
    assert _role_is_allowed(Role.DCS, (Role.GM,), production)
    assert not _role_is_allowed(Role.GM, (Role.ADMIN,), production)
    assert not _role_is_allowed(Role.GM, (Role.MICH,), test)
