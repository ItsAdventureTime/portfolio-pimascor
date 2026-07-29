from sqlalchemy import select

from pimascor_api.models import AuditEvent

from .conftest import TestingSession, sign_in


def test_activity_monitor_is_admin_only_and_excludes_admin_by_default(client):
    sign_in(client, "requester")
    forbidden = client.get("/api/v1/admin/activity")
    assert forbidden.status_code == 403

    sign_in(client, "admin")
    response = client.get("/api/v1/admin/activity?days=7")
    assert response.status_code == 200
    body = response.json()
    assert body["include_admin"] is False
    assert body["active_users"] == 1
    assert {event["actor"]["role"] for event in body["events"] if event["actor"]} == {"REQUESTER"}
    assert body["timeline"]
    assert body["categories"]


def test_activity_monitor_can_include_admin_without_exposing_email(client):
    sign_in(client, "requester")
    sign_in(client, "admin")
    response = client.get("/api/v1/admin/activity?include_admin=true&category=SECURITY")
    assert response.status_code == 200
    body = response.json()
    roles = {event["actor"]["role"] for event in body["events"] if event["actor"]}
    assert {"ADMIN", "REQUESTER"}.issubset(roles)
    assert all("email" not in (event["actor"] or {}) for event in body["events"])


def test_wrong_password_creates_a_privacy_minimized_security_event(client):
    response = client.post(
        "/api/v1/auth/password/start",
        json={"username": "admin", "password": "Definitely-Wrong-123!"},
    )
    assert response.status_code == 401
    with TestingSession() as db:
        event = db.scalar(
            select(AuditEvent).where(AuditEvent.action == "AUTH_PASSWORD_REJECTED")
        )
        assert event is not None
        assert event.reason == "Credentials rejected"
        assert "Wrong" not in (event.reason or "")


def test_only_admin_can_maintain_unique_funding_sources(client):
    dcs_csrf = sign_in(client, "dcs")
    forbidden = client.post(
        "/api/v1/funding-sources",
        json={"name": "BDO Operating •••• 4821"},
        headers={"X-CSRF-Token": dcs_csrf},
    )
    assert forbidden.status_code == 403

    admin_csrf = sign_in(client, "admin")
    created = client.post(
        "/api/v1/funding-sources",
        json={"name": "BDO Operating •••• 4821"},
        headers={"X-CSRF-Token": admin_csrf},
    )
    assert created.status_code == 201
    duplicate = client.post(
        "/api/v1/funding-sources",
        json={"name": "bdo operating •••• 4821"},
        headers={"X-CSRF-Token": admin_csrf},
    )
    assert duplicate.status_code == 409
