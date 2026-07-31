import io
import zipfile

from sqlalchemy import select

from pimascor_api.models import DataExport, DataExportStatus, User
from pimascor_api.services.data_exports import process_one_export

from .conftest import TestingSession, sign_in


def test_admin_can_queue_only_two_local_record_archives_per_ph_week(client, monkeypatch):
    monkeypatch.setattr("pimascor_api.routers.data_exports.get_settings", lambda: type("Settings", (), {"data_export_enabled": True})())
    monkeypatch.setattr("pimascor_api.routers.data_exports.require_storage", lambda: None)
    csrf = sign_in(client, "admin")

    first = client.post("/api/v1/data-exports", headers={"X-CSRF-Token": csrf})
    second = client.post("/api/v1/data-exports", headers={"X-CSRF-Token": csrf})
    third = client.post("/api/v1/data-exports", headers={"X-CSRF-Token": csrf})

    assert first.status_code == 202, first.text
    assert first.json()["status"] == "QUEUED"
    assert second.status_code == 202, second.text
    assert third.status_code == 429, third.text
    assert len(client.get("/api/v1/data-exports").json()) == 2


def test_full_record_archives_are_limited_to_authorized_finance_and_management_roles(client, monkeypatch):
    monkeypatch.setattr("pimascor_api.routers.data_exports.get_settings", lambda: type("Settings", (), {"data_export_enabled": True})())
    monkeypatch.setattr("pimascor_api.routers.data_exports.require_storage", lambda: None)
    csrf = sign_in(client, "requester")
    response = client.get("/api/v1/data-exports")
    assert response.status_code == 403, response.text
    response = client.post("/api/v1/data-exports", headers={"X-CSRF-Token": csrf})
    assert response.status_code == 403, response.text
    csrf = sign_in(client, "mich")
    response = client.post("/api/v1/data-exports", headers={"X-CSRF-Token": csrf})
    assert response.status_code == 202, response.text


def test_demo_explicitly_disables_complete_local_archives(client):
    csrf = sign_in(client, "admin")
    response = client.post("/api/v1/data-exports", headers={"X-CSRF-Token": csrf})
    assert response.status_code == 503, response.text
    assert response.json()["error"]["message"] == "Complete local records archives are disabled in this demo."


def test_worker_creates_csv_and_attachment_ready_archive_without_credentials(monkeypatch):
    captured: dict[str, bytes] = {}
    monkeypatch.setattr("pimascor_api.services.data_exports.require_storage", lambda: None)
    monkeypatch.setattr(
        "pimascor_api.services.data_exports.put_document",
        lambda *, key, fileobj, **_: captured.setdefault(key, fileobj.read()),
    )
    monkeypatch.setattr("pimascor_api.services.data_exports._notify_ready", lambda _: None)
    with TestingSession() as db:
        admin_id = db.scalar(select(User.id).where(User.username == "admin"))
        db.add(DataExport(requested_by_id=admin_id))
        db.commit()
        assert process_one_export(db) is True
        result = db.scalar(__import__("sqlalchemy").select(DataExport))
        assert result.status == DataExportStatus.READY
        archive = zipfile.ZipFile(io.BytesIO(next(iter(captured.values()))))
        assert "records/users.csv" in archive.namelist()
        assert "password_hash" not in archive.read("records/users.csv").decode()
