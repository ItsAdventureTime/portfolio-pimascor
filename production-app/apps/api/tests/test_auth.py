from .conftest import sign_in
from pimascor_api.config import get_settings


def test_password_and_email_code_login(client):
    csrf = sign_in(client)
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["username"] == "admin"
    assert csrf


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
