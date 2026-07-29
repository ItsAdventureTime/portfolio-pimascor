from sqlalchemy import select

from pimascor_api.incident_admin import purge_demo_incidents
from pimascor_api.main import friendly_http_error
from pimascor_api.models import (
    AuditEvent,
    IncidentReport,
    IncidentSeverity,
    IncidentSource,
)

from .conftest import TestingSession, sign_in


def incident_payload():
    return {
        "client_report_id": "5ce2b1e4-2b63-4a9c-b88a-27dc80ad99b6",
        "severity": "RECOVERABLE",
        "operation": "Save a Budget Request",
        "user_action": "The user was trying to save a Budget Request.",
        "user_message": "This record changed after you opened it.",
        "recovery_suggestion": "Refresh the record and review the latest information.",
        "can_continue": True,
        "page_path": "/pimascor/demo/#budget-requests",
        "request_method": "POST",
        "request_path": "/budget-requests/example/submit",
        "http_status": 409,
        "error_code": "HTTP_409",
        "technical_summary": "ApiError; HTTP_409; HTTP 409",
        "client_runtime": "Gecko; online",
        "correlation_id": "08a2ec7f-3f63-46e1-8595-ab95f689017a",
    }


def test_authenticated_user_explicitly_reports_for_investigation(client):
    csrf = sign_in(client, "requester")
    response = client.post(
        "/api/v1/incidents",
        headers={"X-CSRF-Token": csrf},
        json=incident_payload(),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["reference"].startswith("INC-")
    assert body["status"] == "REPORTED"
    assert body["email_admin_sent_at"] is not None
    assert body["email_developer_sent_at"] is not None
    assert "technical_summary" not in body
    assert "user_action" not in body

    with TestingSession() as db:
        incident = db.get(IncidentReport, body["id"])
        assert incident is not None
        assert incident.email_admin_sent_at is not None
        assert incident.email_developer_sent_at is not None
        actions = set(db.scalars(select(AuditEvent.action)).all())
        assert "INCIDENT_REPORTED" in actions


def test_incident_client_id_is_idempotent_per_user(client):
    csrf = sign_in(client, "requester")
    first = client.post(
        "/api/v1/incidents",
        headers={"X-CSRF-Token": csrf},
        json=incident_payload(),
    )
    second = client.post(
        "/api/v1/incidents",
        headers={"X-CSRF-Token": csrf},
        json=incident_payload(),
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    with TestingSession() as db:
        assert len(db.scalars(select(IncidentReport)).all()) == 1


def test_user_cannot_report_another_users_incident(client):
    requester_csrf = sign_in(client, "requester")
    created = client.post(
        "/api/v1/incidents",
        headers={"X-CSRF-Token": requester_csrf},
        json=incident_payload(),
    )
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": requester_csrf})
    gm_csrf = sign_in(client, "gm")
    response = client.post(
        f"/api/v1/incidents/{created.json()['id']}/report",
        headers={"X-CSRF-Token": gm_csrf},
    )
    assert response.status_code == 403
    assert response.json()["error"]["message"] == "Your account cannot complete this action."


def test_detected_server_incident_waits_for_user_before_email(client):
    with TestingSession() as db:
        incident = IncidentReport(
            reference="INC-20260723-SERVER01",
            actor_user_id=None,
            source=IncidentSource.SERVER,
            severity=IncidentSeverity.BLOCKING,
            operation="Complete a PIMASCOR operation",
            user_action="Using POST /api/v1/example",
            user_message="We could not confirm whether the last action finished.",
            recovery_suggestion="Check the relevant list before trying again.",
            can_continue=False,
            page_path="/pimascor/demo/#budget-requests",
            request_method="POST",
            request_path="/api/v1/example",
            http_status=500,
            error_code="UNEXPECTED_ERROR",
            technical_summary="Exception type: RuntimeError",
            client_runtime=None,
            deployment_tier="demo",
            correlation_id="71d9f6eb-5612-4ee3-9ae4-68a381be56af",
        )
        db.add(incident)
        db.commit()
        db.refresh(incident)
        incident_id = incident.id
        assert incident.email_admin_sent_at is None
        assert incident.email_developer_sent_at is None

    csrf = sign_in(client, "requester")
    reported = client.post(
        f"/api/v1/incidents/{incident_id}/report",
        headers={"X-CSRF-Token": csrf},
    )
    assert reported.status_code == 200, reported.text
    assert reported.json()["email_admin_sent_at"] is not None
    assert reported.json()["email_developer_sent_at"] is not None

    with TestingSession() as db:
        actions = set(db.scalars(select(AuditEvent.action)).all())
        assert "INCIDENT_REPORTED" in actions


def test_incident_requires_csrf(client):
    sign_in(client, "requester")
    response = client.post("/api/v1/incidents", json=incident_payload())
    assert response.status_code == 403
    assert response.json()["error"]["message"] == "Your account cannot complete this action."


def test_duplicate_configuration_error_is_plain_and_actionable():
    message, recovery, can_continue = friendly_http_error(
        409,
        "Funding source already exists",
    )
    assert message == "That approved funding source is already on the list."
    assert recovery == "Use the existing source, or enter a different approved display name."
    assert can_continue is True


def test_demo_incident_purge_removes_only_incidents_and_their_audit_events(client):
    csrf = sign_in(client, "requester")
    created = client.post(
        "/api/v1/incidents",
        headers={"X-CSRF-Token": csrf},
        json=incident_payload(),
    )
    assert created.status_code == 201

    with TestingSession() as db:
        unrelated = AuditEvent(
            actor_user_id=None,
            action="FUNDING_SOURCE_CREATED",
            entity_type="funding_source",
            entity_id="source-1",
            reason="Unrelated control event",
        )
        db.add(unrelated)
        db.commit()

        result = purge_demo_incidents(
            db,
            deployment_tier="demo",
            confirmation="DELETE-DEMO-INCIDENTS",
        )
        assert result.incidents == 1
        assert result.audit_events == 1
        assert db.scalar(select(IncidentReport)) is None
        remaining = list(db.scalars(select(AuditEvent)).all())
        assert all(event.entity_type != "incident" for event in remaining)
        assert any(event.entity_type == "funding_source" for event in remaining)


def test_incident_purge_refuses_non_demo_deployments():
    with TestingSession() as db:
        try:
            purge_demo_incidents(
                db,
                deployment_tier="production",
                confirmation="DELETE-DEMO-INCIDENTS",
            )
        except RuntimeError as exc:
            assert str(exc) == "Incident cleanup is restricted to the demo deployment."
        else:
            raise AssertionError("Production incident cleanup should have been refused.")
