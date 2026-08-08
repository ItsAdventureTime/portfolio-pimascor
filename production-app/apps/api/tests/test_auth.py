from .conftest import TestingSession, sign_in
from pimascor_api.config import get_settings
from pimascor_api.models import User
from pimascor_api.security import verify_password


def test_password_and_email_code_login(client):
    csrf = sign_in(client)
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["username"] == "admin"
    assert csrf


def test_demo_session_requires_demo_tier_and_creates_normal_session(client):
    settings = get_settings()
    original_tier = settings.deployment_tier
    try:
        settings.deployment_tier = "production"
        unavailable = client.post("/api/v1/auth/demo")
        assert unavailable.status_code == 404

        settings.deployment_tier = "demo"
        entered = client.post("/api/v1/auth/demo")
        assert entered.status_code == 200, entered.text
        assert entered.json()["user"]["username"] == "admin"
        assert "pimascor_session" in client.cookies
        assert client.get("/api/v1/auth/me").status_code == 200
    finally:
        settings.deployment_tier = original_tier


def test_email_code_expires_in_five_minutes(client):
    response = client.post(
        "/api/v1/auth/password/start",
        json={"username": "admin", "password": "Correct-Horse-123!"},
    )
    assert response.status_code == 200
    assert response.json()["expires_in_seconds"] == 300


def test_wrong_password_is_rejected(client):
    response = client.post(
        "/api/v1/auth/password/start",
        json={"username": "admin", "password": "Definitely-Wrong-123!"},
    )
    assert response.status_code == 401


def test_csrf_is_required_for_logout(client):
    sign_in(client)
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 403


def test_logout_returns_204_clears_session_and_revokes_access(client):
    csrf = sign_in(client)
    response = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    assert response.status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401


def test_deployment_specific_cookie_names_are_honored(client):
    settings = get_settings()
    original_session_name = settings.session_cookie_name
    original_csrf_name = settings.csrf_cookie_name
    settings.session_cookie_name = "bridge_ph_pimascor_demo_session"
    settings.csrf_cookie_name = "bridge_ph_pimascor_demo_csrf"
    try:
        sign_in(client)
        assert "bridge_ph_pimascor_demo_session" in client.cookies
        assert client.get("/api/v1/auth/me").status_code == 200
    finally:
        settings.session_cookie_name = original_session_name
        settings.csrf_cookie_name = original_csrf_name


def test_pending_account_activation_sets_password_after_email_code(client):
    with TestingSession() as db:
        user = db.query(User).filter(User.username == "requester").one()
        user.must_set_password = True
        db.commit()

    started = client.post("/api/v1/auth/activation/start", json={"username": "requester"})
    assert started.status_code == 200, started.text
    body = started.json()
    completed = client.post(
        "/api/v1/auth/activation/complete",
        json={
            "challenge_id": body["challenge_id"],
            "code": body["development_code"],
            "password": "New-Activation-Password-2026!",
        },
    )
    assert completed.status_code == 200, completed.text
    with TestingSession() as db:
        user = db.query(User).filter(User.username == "requester").one()
        assert user.must_set_password is False
        assert verify_password(user.password_hash, "New-Activation-Password-2026!")


def test_activation_challenge_cannot_be_used_as_normal_login_code(client):
    with TestingSession() as db:
        user = db.query(User).filter(User.username == "requester").one()
        user.must_set_password = True
        db.commit()
    started = client.post("/api/v1/auth/activation/start", json={"username": "requester"})
    assert started.status_code == 200
    response = client.post(
        "/api/v1/auth/email-code/verify",
        json={"challenge_id": started.json()["challenge_id"], "code": started.json()["development_code"]},
    )
    assert response.status_code == 400


def test_password_reset_response_does_not_disclose_account_existence(client):
    known = client.post("/api/v1/auth/password-reset/start", json={"identifier": "admin"})
    unknown = client.post("/api/v1/auth/password-reset/start", json={"identifier": "missing@example.com"})
    assert known.status_code == unknown.status_code == 200
    assert known.json()["message"] == unknown.json()["message"]
    assert known.json()["expires_in_seconds"] == 900
    assert known.json()["development_code"]
    assert unknown.json()["development_code"] is None


def test_password_reset_consumes_token_and_revokes_existing_sessions(client):
    sign_in(client)
    started = client.post("/api/v1/auth/password-reset/start", json={"identifier": "admin"})
    assert started.status_code == 200, started.text
    body = started.json()
    completed = client.post(
        "/api/v1/auth/password-reset/complete",
        json={
            "challenge_id": body["development_challenge_id"],
            "token": body["development_code"],
            "password": "New-Recovery-Password-2026!",
            "confirmation": "New-Recovery-Password-2026!",
        },
    )
    assert completed.status_code == 200, completed.text
    assert client.get("/api/v1/auth/me").status_code == 401

    next_start = client.post(
        "/api/v1/auth/password/start",
        json={"username": "admin", "password": "New-Recovery-Password-2026!"},
    )
    assert next_start.status_code == 200, next_start.text


def test_password_reset_token_is_single_use_and_wrong_tokens_are_generic(client):
    started = client.post("/api/v1/auth/password-reset/start", json={"identifier": "admin"})
    body = started.json()
    wrong = client.post(
        "/api/v1/auth/password-reset/complete",
        json={
            "challenge_id": body["development_challenge_id"],
            "token": "x" * 43,
            "password": "New-Recovery-Password-2026!",
            "confirmation": "New-Recovery-Password-2026!",
        },
    )
    assert wrong.status_code == 400
    wrong_body = wrong.json()
    assert (wrong_body.get("detail") or wrong_body["error"]["message"]) == (
        "This password reset link is no longer valid."
    )
    valid = client.post(
        "/api/v1/auth/password-reset/complete",
        json={
            "challenge_id": body["development_challenge_id"],
            "token": body["development_code"],
            "password": "New-Recovery-Password-2026!",
            "confirmation": "New-Recovery-Password-2026!",
        },
    )
    assert valid.status_code == 200
    reused = client.post(
        "/api/v1/auth/password-reset/complete",
        json={
            "challenge_id": body["development_challenge_id"],
            "token": body["development_code"],
            "password": "Another-Recovery-Password-2026!",
            "confirmation": "Another-Recovery-Password-2026!",
        },
    )
    assert reused.status_code == 400


def test_release_update_is_shown_once_per_user_after_acknowledgement(client):
    csrf = sign_in(client)
    first = client.get("/api/v1/auth/release-updates")
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["id"] == "2026-08-03-responsive-workspace"
    assert body["released_on"] == "2026-08-03"
    assert any(change["kind"] == "new" for change in body["changes"])
    assert any(change["title"] == "Sign in faster on a phone" for change in body["changes"])

    acknowledged = client.post(
        "/api/v1/auth/release-updates/ack",
        headers={"X-CSRF-Token": csrf},
    )
    assert acknowledged.status_code == 204, acknowledged.text
    second = client.get("/api/v1/auth/release-updates")
    assert second.status_code == 200
    assert second.json() is None


def test_release_update_ack_requires_csrf(client):
    sign_in(client)
    response = client.post("/api/v1/auth/release-updates/ack")
    assert response.status_code == 403
