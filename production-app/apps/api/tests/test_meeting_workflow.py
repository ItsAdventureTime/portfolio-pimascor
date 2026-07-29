from .conftest import sign_in


def test_accepted_quotation_precedes_mich_and_gm_budget_approval(client, monkeypatch):
    monkeypatch.setattr("pimascor_api.routers.quotations.put_document", lambda **_: None)
    requester_headers = {"X-CSRF-Token": sign_in(client, "requester")}
    configured_client = client.get("/api/v1/clients").json()[0]

    quotation = client.post(
        "/api/v1/quotations",
        headers=requester_headers,
        json={
            "client_id": configured_client["id"],
            "shipment_reference": "ACT-172",
            "quoted_amount": "65000.00",
            "currency": "PHP",
            "terms_and_conditions": "Payment is due within thirty days after Billing.",
        },
    )
    assert quotation.status_code == 201, quotation.text
    submitted = client.post(
        f"/api/v1/quotations/{quotation.json()['id']}/submit",
        params={"expected_version": quotation.json()["version"]},
        headers=requester_headers,
    )
    assert submitted.json()["status"] == "PENDING_APPROVAL"

    gm_headers = {"X-CSRF-Token": sign_in(client, "gm")}
    approved = client.post(
        f"/api/v1/quotations/{quotation.json()['id']}/decision",
        headers=gm_headers,
        json={"expected_version": submitted.json()["version"], "approve": True},
    )
    assert approved.json()["status"] == "APPROVED"

    requester_headers = {"X-CSRF-Token": sign_in(client, "requester")}
    accepted = client.post(
        f"/api/v1/quotations/{quotation.json()['id']}/client-acceptance",
        headers=requester_headers,
        data={
            "expected_version": approved.json()["version"],
            "accepted_on": "2026-07-24",
            "client_signatory": "Client Representative",
        },
        files={"document": ("accepted.pdf", b"%PDF-1.4\naccepted quotation", "application/pdf")},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "CLIENT_ACCEPTED"

    sign_in(client, "mich")
    library = client.get("/api/v1/documents")
    signed_contract = next(
        item for item in library.json() if item["reference"] == quotation.json()["reference"]
    )
    assert signed_contract["kind"] == "SIGNED_QUOTATION"
    assert signed_contract["file_name"] == "accepted.pdf"

    requester_headers = {"X-CSRF-Token": sign_in(client, "requester")}
    budget = client.post(
        "/api/v1/budget-requests",
        headers=requester_headers,
        json={
            "client_id": configured_client["id"],
            "quotation_id": quotation.json()["id"],
            "shipment_reference": "ACT-172",
            "request_date": "2026-07-24",
            "items": [
                {"kind": "BUYING", "description": "Port charges", "amount": "50000.00"},
                {"kind": "SELLING", "description": "Client charge", "amount": "65000.00"},
            ],
        },
    )
    assert budget.status_code == 201, budget.text
    submitted_budget = client.post(
        f"/api/v1/budget-requests/{budget.json()['id']}/submit",
        params={"expected_version": budget.json()["version"]},
        headers=requester_headers,
    )
    assert submitted_budget.json()["status"] == "PENDING_REVIEW"

    mich_headers = {"X-CSRF-Token": sign_in(client, "mich")}
    reviewed = client.post(
        f"/api/v1/budget-reviews/{budget.json()['id']}/review",
        headers=mich_headers,
        json={
            "expected_version": submitted_budget.json()["version"],
            "reason": "Initial processor entry and quotation checked",
        },
    )
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["status"] == "PENDING_APPROVAL"
    assert reviewed.json()["reviewed_by"]["role"] == "MICH"

    gm_headers = {"X-CSRF-Token": sign_in(client, "gm")}
    decided = client.post(
        f"/api/v1/approvals/{budget.json()['id']}/approve",
        headers=gm_headers,
        json={"expected_version": reviewed.json()["version"]},
    )
    assert decided.status_code == 200, decided.text
    assert decided.json()["status"] == "APPROVED"


def test_dcs_override_is_visible_reasoned_and_exceptional(client):
    requester_headers = {"X-CSRF-Token": sign_in(client, "requester")}
    configured_client = client.get("/api/v1/clients").json()[0]
    budget = client.post(
        "/api/v1/budget-requests",
        headers=requester_headers,
        json={
            "client_id": configured_client["id"],
            "shipment_reference": "ACT-173",
            "request_date": "2026-07-24",
            "items": [{"kind": "BUYING", "description": "Port charges", "amount": "1000.00"}],
        },
    ).json()
    submitted = client.post(
        f"/api/v1/budget-requests/{budget['id']}/submit",
        params={"expected_version": budget["version"]},
        headers=requester_headers,
    ).json()

    dcs_headers = {"X-CSRF-Token": sign_in(client, "dcs")}
    visible = client.get("/api/v1/approvals/queue")
    assert any(item["id"] == budget["id"] for item in visible.json())
    rejected = client.post(
        f"/api/v1/approvals/{budget['id']}/dcs-override",
        headers=dcs_headers,
        json={"expected_version": submitted["version"], "reason": "GM away"},
    )
    assert rejected.status_code == 422
    approved = client.post(
        f"/api/v1/approvals/{budget['id']}/dcs-override",
        headers=dcs_headers,
        json={
            "expected_version": submitted["version"],
            "reason": "Mich and the GM are unavailable for an urgent port release",
        },
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "APPROVED"
