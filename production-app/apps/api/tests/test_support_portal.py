from datetime import timedelta
import secrets

from sqlalchemy import select

from pimascor_api.config import get_settings
from pimascor_api.models import SupportTicket, SupportTicketPortalToken, utc_now
from pimascor_api.security import hash_secret

from .conftest import TestingSession, sign_in


def test_demo_create_exposes_a_synthetic_portal_link_only(client):
    settings = get_settings()
    original_tier = settings.deployment_tier
    settings.deployment_tier = "demo"
    try:
        csrf = sign_in(client, "requester")
        response = client.post(
            "/api/v1/support-tickets",
            headers={"X-CSRF-Token": csrf},
            json={"subject": "Demo portal", "message": "Open the simulated thread."},
        )
        assert response.status_code == 201, response.text
        portal_url = response.json()["portal_url"]
        assert portal_url.startswith(settings.public_app_url.rstrip("/") + "/#support-portal?")
    finally:
        settings.deployment_tier = original_tier


def test_requester_portal_reads_and_replies_without_a_session(client):
    csrf = sign_in(client, "requester")
    created = client.post(
        "/api/v1/support-tickets",
        headers={"X-CSRF-Token": csrf},
        json={
            "category": "WORKFLOW",
            "reason": "I NEED HELP COMPLETING A TASK",
            "subject": "Portal access",
            "message": "Please review this **Markdown** question.",
        },
    )
    assert created.status_code == 201, created.text
    ticket_id = created.json()["id"]

    raw_token = secrets.token_urlsafe(32)
    with TestingSession() as db:
        ticket = db.scalar(select(SupportTicket).where(SupportTicket.id == ticket_id))
        db.add(
            SupportTicketPortalToken(
                ticket_id=ticket_id,
                token_hash=hash_secret(raw_token),
                audience="requester",
                recipient_key="requester",
                recipient_email=ticket.requester.email,
                recipient_label=ticket.requester.display_name,
                recipient_user_id=ticket.requester_id,
                expires_at=utc_now() + timedelta(days=1),
            )
        )
        db.commit()

    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    portal = client.get(f"/api/v1/support-tickets/portal/{ticket_id}", headers={"X-Support-Token": raw_token})
    assert portal.status_code == 200, portal.text
    assert portal.json()["viewer_audience"] == "requester"
    assert portal.json()["can_reply"] is True

    query_only = client.get(f"/api/v1/support-tickets/portal/{ticket_id}?token={raw_token}")
    assert query_only.status_code == 401

    reply = client.post(
        f"/api/v1/support-tickets/portal/{ticket_id}/replies",
        headers={"X-Support-Token": raw_token},
        json={"body": "Here is a follow-up with `details`."},
    )
    assert reply.status_code == 200, reply.text
    assert reply.json()["replies"][-1]["body"] == "Here is a follow-up with `details`."

    malformed = client.post(
        f"/api/v1/support-tickets/portal/{ticket_id}/replies",
        headers={"X-Support-Token": raw_token, "Content-Type": "application/json"},
        content="{",
    )
    assert malformed.status_code == 422


def test_demo_style_multipart_attachment_is_explicitly_simulated(client):
    csrf = sign_in(client, "requester")
    response = client.post(
        "/api/v1/support-tickets",
        headers={"X-CSRF-Token": csrf},
        data={
            "category": "SUGGESTION",
            "reason": "I HAVE A PRODUCT IMPROVEMENT IDEA",
            "subject": "A small idea",
            "message": "Could we add a quick link?",
        },
        files={"attachments": ("notes.txt", b"plain text evidence", "text/plain")},
    )
    assert response.status_code == 201, response.text
    assert response.json()["message_attachments"][0]["simulated"] is True
