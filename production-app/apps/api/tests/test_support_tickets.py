from sqlalchemy import select

from pimascor_api.config import get_settings
from pimascor_api.models import AuditEvent, SupportTicket, SupportTicketReply, User

from .conftest import TestingSession, sign_in


def create_ticket(client, csrf: str, subject: str = "Need help", message: str = "Please help with this workflow"):
    return client.post(
        "/api/v1/support-tickets",
        headers={"X-CSRF-Token": csrf},
        json={"subject": subject, "message": message},
    )


def test_authenticated_users_create_and_only_see_their_own_tickets(client):
    requester_csrf = sign_in(client, "requester")
    created = create_ticket(client, requester_csrf)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["ticket_number"].startswith("SUP-")
    assert body["requester_role"] == "REQUESTER"
    assert body["status"] == "OPEN"
    assert body["replies"] == []

    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": requester_csrf})
    gm_csrf = sign_in(client, "gm")
    assert client.get("/api/v1/support-tickets").json() == []
    assert client.get(f"/api/v1/support-tickets/{body['id']}").status_code == 403

    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": gm_csrf})
    admin_csrf = sign_in(client, "admin")
    listed = client.get("/api/v1/support-tickets")
    assert listed.status_code == 200
    assert [ticket["id"] for ticket in listed.json()] == [body["id"]]


def test_admin_assignment_reply_status_lifecycle_and_audit(client):
    requester_csrf = sign_in(client, "requester")
    created = create_ticket(client, requester_csrf)
    ticket = created.json()
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": requester_csrf})
    admin_csrf = sign_in(client, "admin")

    with TestingSession() as db:
        admin_id = db.scalar(select(User.id).where(User.username == "admin"))

    assigned = client.patch(
        f"/api/v1/support-tickets/{ticket['id']}/assignment",
        headers={"X-CSRF-Token": admin_csrf},
        json={"assigned_to_id": admin_id, "expected_version": 1},
    )
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["assigned_to"]["username"] == "admin"

    replied = client.post(
        f"/api/v1/support-tickets/{ticket['id']}/reply",
        headers={"X-CSRF-Token": admin_csrf},
        json={"body": "We are looking into this.", "expected_version": 2},
    )
    assert replied.status_code == 200, replied.text
    assert replied.json()["replies"][0]["body"] == "We are looking into this."

    in_progress = client.patch(
        f"/api/v1/support-tickets/{ticket['id']}/status",
        headers={"X-CSRF-Token": admin_csrf},
        json={"status": "IN_PROGRESS", "expected_version": 3},
    )
    assert in_progress.status_code == 200, in_progress.text
    resolved = client.post(
        f"/api/v1/support-tickets/{ticket['id']}/resolve",
        headers={"X-CSRF-Token": admin_csrf},
        json={"expected_version": 4},
    )
    assert resolved.status_code == 200, resolved.text
    closed = client.post(
        f"/api/v1/support-tickets/{ticket['id']}/close",
        headers={"X-CSRF-Token": admin_csrf},
        json={"expected_version": 5},
    )
    assert closed.status_code == 200, closed.text
    reopened = client.post(
        f"/api/v1/support-tickets/{ticket['id']}/reopen",
        headers={"X-CSRF-Token": admin_csrf},
        json={"expected_version": 6},
    )
    assert reopened.status_code == 200, reopened.text
    assert reopened.json()["status"] == "OPEN"

    with TestingSession() as db:
        actions = set(db.scalars(select(AuditEvent.action)).all())
        assert {
            "SUPPORT_TICKET_CREATED",
            "SUPPORT_TICKET_ASSIGNED",
            "SUPPORT_TICKET_REPLIED",
            "SUPPORT_TICKET_STARTED",
            "SUPPORT_TICKET_RESOLVED",
            "SUPPORT_TICKET_CLOSED",
            "SUPPORT_TICKET_REOPENED",
        } <= actions


def test_internal_replies_are_hidden_from_requesters_and_append_only(client):
    requester_csrf = sign_in(client, "requester")
    created = create_ticket(client, requester_csrf)
    ticket = created.json()
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": requester_csrf})
    admin_csrf = sign_in(client, "admin")

    response = client.post(
        f"/api/v1/support-tickets/{ticket['id']}/reply",
        headers={"X-CSRF-Token": admin_csrf},
        json={"body": "Internal triage note", "is_internal": True, "expected_version": 1},
    )
    assert response.status_code == 200, response.text
    assert response.json()["replies"][0]["is_internal"] is True

    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": admin_csrf})
    requester_csrf = sign_in(client, "requester")
    requester_view = client.get(f"/api/v1/support-tickets/{ticket['id']}")
    assert requester_view.status_code == 200
    assert requester_view.json()["replies"] == []

    with TestingSession() as db:
        assert len(db.scalars(select(SupportTicketReply)).all()) == 1


def test_csrf_and_concurrency_are_enforced(client):
    csrf = sign_in(client, "requester")
    missing_csrf = client.post(
        "/api/v1/support-tickets",
        json={"subject": "Need help", "message": "Please help"},
    )
    assert missing_csrf.status_code == 403

    created = create_ticket(client, csrf)
    assert created.status_code == 201
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    admin_csrf = sign_in(client, "admin")
    response = client.patch(
        f"/api/v1/support-tickets/{created.json()['id']}/status",
        headers={"X-CSRF-Token": admin_csrf},
        json={"status": "IN_PROGRESS", "expected_version": 99},
    )
    assert response.status_code == 409


def test_demo_admin_replies_are_labeled_and_do_not_send_email(client):
    settings = get_settings()
    original_tier = settings.deployment_tier
    settings.deployment_tier = "demo"
    try:
        requester_csrf = sign_in(client, "requester")
        created = create_ticket(client, requester_csrf)
        assert created.status_code == 201
        client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": requester_csrf})
        admin_csrf = sign_in(client, "admin")
        response = client.post(
            f"/api/v1/support-tickets/{created.json()['id']}/reply",
            headers={"X-CSRF-Token": admin_csrf},
                json={"body": "Synthetic demo response", "expected_version": 2},
        )
        assert response.status_code == 200, response.text
        reply = response.json()["replies"][0]
        assert reply["is_simulated"] is True
        assert reply["body"].startswith("[DEMO SIMULATED REPLY]")
        with TestingSession() as db:
            ticket = db.scalar(select(SupportTicket))
            stored_reply = db.scalar(select(SupportTicketReply))
            assert ticket.email_admin_sent_at is None
            assert stored_reply.email_admin_sent_at is None
    finally:
        settings.deployment_tier = original_tier
