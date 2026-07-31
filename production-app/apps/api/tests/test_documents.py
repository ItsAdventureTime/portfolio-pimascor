from io import BytesIO

from .conftest import sign_in
from .test_operational_workflows import approved_budget


def test_document_library_lists_uploaded_file_and_uses_short_lived_inline_view(client, monkeypatch):
    document_bytes = b"%PDF-1.4\nverified demo"

    monkeypatch.setattr("pimascor_api.routers.operations.put_document", lambda **_: None)
    monkeypatch.setattr("pimascor_api.routers.documents.storage_configured", lambda: True)

    def open_document(*, byte_range=None, **_):
        content = document_bytes
        if byte_range:
            start, end = (int(value) for value in byte_range.removeprefix("bytes=").split("-"))
            content = content[start:end + 1]
        return {
            "Body": BytesIO(content),
            "ContentLength": len(content),
            "ContentType": "application/pdf",
        }

    monkeypatch.setattr("pimascor_api.routers.documents.open_document", open_document)

    budget, _ = approved_budget(client)
    dcs_csrf = sign_in(client, "dcs")
    paid = client.post(
        f"/api/v1/dcs-payments/budget/{budget['id']}/pay",
        headers={"X-CSRF-Token": dcs_csrf},
        json={
            "amount": "50000.00",
            "paid_on": "2026-07-23",
            "mode": "Bank transfer",
            "source": "Operating bank account",
            "recipient": "Port operator",
            "transaction_reference": "DOC-LIBRARY-001",
            "expected_version": budget["version"],
        },
    )
    assert paid.status_code == 200, paid.text

    requester_csrf = sign_in(client, "requester")
    draft = client.post(
        f"/api/v1/liquidations/budget/{budget['id']}",
        headers={"X-CSRF-Token": requester_csrf},
        json={"lines": [{"description": "Port charge", "amount": "50000.00"}]},
    )
    uploaded = client.post(
        f"/api/v1/liquidations/{draft.json()['id']}/evidence",
        headers={"X-CSRF-Token": requester_csrf},
        data={"expected_version": str(draft.json()["version"]), "kind": "RECEIPT"},
        files={"document": ("port-receipt.pdf", document_bytes, "application/pdf")},
    )
    assert uploaded.status_code == 200, uploaded.text

    sign_in(client, "mich")
    library = client.get("/api/v1/documents")
    assert library.status_code == 200, library.text
    assert library.json()[0]["file_name"] == "port-receipt.pdf"
    assert library.json()[0]["available"] is True
    assert library.json()[0]["size_bytes"] > 0

    view = client.get(f"/api/v1/documents/{library.json()[0]['id']}/view")
    assert view.status_code == 200
    assert view.headers["cache-control"] == "private, no-store, max-age=0"
    assert view.headers["accept-ranges"] == "bytes"
    assert int(view.headers["content-length"]) == len(document_bytes)
    assert view.headers["content-disposition"].startswith("inline;")
    assert view.headers["content-type"].startswith("application/pdf")
    assert view.content.startswith(b"%PDF-")
    assert "content-security-policy" not in view.headers

    partial = client.get(
        f"/api/v1/documents/{library.json()[0]['id']}/view",
        headers={"Range": "bytes=0-7"},
    )
    assert partial.status_code == 206
    assert partial.content == document_bytes[:8]
    assert partial.headers["content-range"] == f"bytes 0-7/{len(document_bytes)}"
    assert partial.headers["content-length"] == "8"

    unavailable_range = client.get(
        f"/api/v1/documents/{library.json()[0]['id']}/view",
        headers={"Range": "bytes=999999-"},
    )
    assert unavailable_range.status_code == 416
    assert unavailable_range.headers["content-range"] == f"bytes */{len(document_bytes)}"

    download = client.get(f"/api/v1/documents/{library.json()[0]['id']}/download")
    assert download.status_code == 200
    assert download.headers["content-disposition"].startswith("attachment;")
    assert download.content == document_bytes

    sign_in(client, "requester")
    denied = client.get(f"/api/v1/documents/{library.json()[0]['id']}/download")
    assert denied.status_code == 403


def test_document_upload_rejects_mismatched_file_contents(client, monkeypatch):
    monkeypatch.setattr("pimascor_api.routers.operations.put_document", lambda **_: None)
    budget, _ = approved_budget(client)
    dcs_csrf = sign_in(client, "dcs")
    paid = client.post(
        f"/api/v1/dcs-payments/budget/{budget['id']}/pay",
        headers={"X-CSRF-Token": dcs_csrf},
        json={
            "amount": "50000.00",
            "paid_on": "2026-07-23",
            "mode": "Bank transfer",
            "source": "Operating bank account",
            "recipient": "Port operator",
            "transaction_reference": "DOC-LIBRARY-002",
            "expected_version": budget["version"],
        },
    )
    assert paid.status_code == 200
    requester_csrf = sign_in(client, "requester")
    draft = client.post(
        f"/api/v1/liquidations/budget/{budget['id']}",
        headers={"X-CSRF-Token": requester_csrf},
        json={"lines": [{"description": "Port charge", "amount": "50000.00"}]},
    )
    rejected = client.post(
        f"/api/v1/liquidations/{draft.json()['id']}/evidence",
        headers={"X-CSRF-Token": requester_csrf},
        data={"expected_version": str(draft.json()["version"]), "kind": "RECEIPT"},
        files={"document": ("not-really.pdf", b"plain text", "application/pdf")},
    )
    assert rejected.status_code == 422
