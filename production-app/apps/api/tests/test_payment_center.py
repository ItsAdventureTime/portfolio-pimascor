from .conftest import review_budget, sign_in


def create_approved_budget(client):
    requester_csrf = sign_in(client, "requester")
    client_id = client.get("/api/v1/clients").json()[0]["id"]
    created = client.post(
        "/api/v1/budget-requests",
        headers={"X-CSRF-Token": requester_csrf},
        json={
            "client_id": client_id,
            "shipment_reference": "PAYMENT-CENTER-SHIPMENT",
            "request_date": "2026-07-21",
            "currency": "PHP",
            "items": [
                {"kind": "BUYING", "description": "Original buying budget", "amount": "50000.00"},
                {"kind": "SELLING", "description": "Client selling amount", "amount": "70000.00"},
            ],
        },
    ).json()
    submitted = client.post(
        f"/api/v1/budget-requests/{created['id']}/submit",
        params={"expected_version": created["version"]},
        headers={"X-CSRF-Token": requester_csrf},
    ).json()
    submitted = review_budget(client, submitted)
    gm_csrf = sign_in(client, "gm")
    return client.post(
        f"/api/v1/approvals/{created['id']}/approve",
        headers={"X-CSRF-Token": gm_csrf},
        json={"expected_version": submitted["version"], "reason": "Budget verified"},
    ).json()


def test_additional_budget_preserves_parent_and_enters_payment_center(client):
    parent = create_approved_budget(client)
    requester_csrf = sign_in(client, "requester")
    created = client.post(
        f"/api/v1/budget-requests/{parent['id']}/additional-budgets",
        headers={"X-CSRF-Token": requester_csrf},
        json={
            "request_date": "2026-07-21",
            "reason": "Unexpected storage after weather delay",
            "related_expense_description": "Port storage liquidation expense",
            "related_expense_amount": "13000.00",
            "items": [
                {"kind": "BUYING", "description": "Additional port storage", "amount": "13000.00"}
            ],
        },
    )
    assert created.status_code == 201, created.text
    additional = created.json()
    assert additional["budget_kind"] == "ADDITIONAL"
    assert additional["parent_budget_id"] == parent["id"]
    assert additional["reference"].startswith("ABR-2026-")

    submitted = client.post(
        f"/api/v1/budget-requests/{additional['id']}/submit",
        params={"expected_version": additional["version"]},
        headers={"X-CSRF-Token": requester_csrf},
    ).json()
    submitted = review_budget(client, submitted)
    gm_csrf = sign_in(client, "gm")
    approved = client.post(
        f"/api/v1/approvals/{additional['id']}/approve",
        headers={"X-CSRF-Token": gm_csrf},
        json={"expected_version": submitted["version"], "reason": "Variance supported"},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["payment_status"] == "PENDING"

    dcs_csrf = sign_in(client, "dcs")
    queue = client.get("/api/v1/dcs-payments")
    assert queue.status_code == 200, queue.text
    additional_item = next(item for item in queue.json() if item["record_id"] == additional["id"])
    assert additional_item["source_type"] == "ADDITIONAL_BUDGET"
    assert additional_item["parent_reference"] == parent["reference"]

    paid = client.post(
        f"/api/v1/dcs-payments/budget/{additional['id']}/pay",
        headers={"X-CSRF-Token": dcs_csrf},
        json={
            "amount": "13000.00",
            "paid_on": "2026-07-21",
            "mode": "Bank transfer",
                "source": "Operating bank account",
            "recipient": "Port operator",
            "transaction_reference": "DCS-ABR-TEST-001",
            "notes": "Updated statement verified",
            "expected_version": approved.json()["version"],
        },
    )
    assert paid.status_code == 200, paid.text
    assert paid.json()["payment_status"] == "PAID"
    assert paid.json()["outstanding_amount"] == "0.00"


def test_dcs_can_hold_annotate_and_return_without_erasing_gm_approval(client):
    budget = create_approved_budget(client)
    dcs_csrf = sign_in(client, "dcs")

    held = client.post(
        f"/api/v1/dcs-payments/budget/{budget['id']}/actions",
        headers={"X-CSRF-Token": dcs_csrf},
        json={
            "action": "HOLD",
            "note": "Awaiting updated bank details",
            "expected_version": budget["version"],
        },
    )
    assert held.status_code == 200, held.text
    assert held.json()["payment_status"] == "ON_HOLD"
    assert held.json()["annotations"][0]["note"] == "Awaiting updated bank details"

    returned = client.post(
        f"/api/v1/dcs-payments/budget/{budget['id']}/actions",
        headers={"X-CSRF-Token": dcs_csrf},
        json={
            "action": "RETURN",
            "note": "Recipient details must be corrected",
            "expected_version": held.json()["version"],
        },
    )
    assert returned.status_code == 200, returned.text
    assert returned.json()["payment_status"] == "RETURNED"

    requester_csrf = sign_in(client, "requester")
    source = client.get(f"/api/v1/budget-requests/{budget['id']}")
    assert source.status_code == 200
    assert source.json()["status"] == "APPROVED"
    assert source.json()["payment_status"] == "RETURNED"

    forbidden = client.post(
        f"/api/v1/dcs-payments/budget/{budget['id']}/actions",
        headers={"X-CSRF-Token": requester_csrf},
        json={"action": "NOTE", "note": "Not allowed", "expected_version": returned.json()["version"]},
    )
    assert forbidden.status_code == 403


def test_dcs_attaches_verified_payment_proof_after_recording_payment(client, monkeypatch):
    monkeypatch.setattr("pimascor_api.routers.payments.put_document", lambda **_: None)
    budget = create_approved_budget(client)
    dcs_csrf = sign_in(client, "dcs")

    paid = client.post(
        f"/api/v1/dcs-payments/budget/{budget['id']}/pay",
        headers={"X-CSRF-Token": dcs_csrf},
        json={
            "amount": "50000.00",
            "paid_on": "2026-07-21",
            "mode": "Bank transfer",
            "source": "Operating bank account",
            "recipient": "Acme Shipping",
            "transaction_reference": "DCS-PROOF-001",
            "notes": "Bank transfer completed",
            "expected_version": budget["version"],
        },
    )
    assert paid.status_code == 200, paid.text
    assert paid.json()["proof_available"] is False

    proof = client.post(
        f"/api/v1/dcs-payments/budget/{budget['id']}/proof",
        headers={"X-CSRF-Token": dcs_csrf},
        data={"expected_version": str(paid.json()["version"])},
        files={"document": ("bank-confirmation.pdf", b"%PDF-1.7\nproof", "application/pdf")},
    )
    assert proof.status_code == 200, proof.text
    assert proof.json()["proof_available"] is True
    assert proof.json()["proof_file_name"] == "bank-confirmation.pdf"

    sign_in(client, "mich")
    library = client.get("/api/v1/documents")
    payment_document = next(
        item for item in library.json() if item["reference"] == budget["reference"]
    )
    assert payment_document["kind"] == "PAYMENT_PROOF"
    assert payment_document["file_name"] == "bank-confirmation.pdf"

    requester_csrf = sign_in(client, "requester")
    confidential = client.get(f"/api/v1/documents/{payment_document['id']}/view")
    assert confidential.status_code == 403
    denied = client.post(
        f"/api/v1/dcs-payments/budget/{budget['id']}/proof",
        headers={"X-CSRF-Token": requester_csrf},
        data={"expected_version": str(proof.json()["version"])},
        files={"document": ("replacement.pdf", b"%PDF-1.7\nproof", "application/pdf")},
    )
    assert denied.status_code == 403


def test_requester_cannot_create_accounting_expense(client):
    csrf = sign_in(client, "requester")
    response = client.post(
        "/api/v1/expense-requests",
        headers={"X-CSRF-Token": csrf},
        json={
            "expense_type": "OPEX",
            "request_date": "2026-07-21",
            "party": "Supplier",
            "purpose": "Office expense",
            "requested_source": "Operating account",
            "amount": "1000.00",
        },
    )
    assert response.status_code == 403


def test_gm_cannot_act_in_dcs_payment_and_dcs_can_hold_with_reason(client):
    budget = create_approved_budget(client)
    gm_csrf = sign_in(client, "gm")
    denied = client.post(
        f"/api/v1/dcs-payments/budget/{budget['id']}/actions",
        headers={"X-CSRF-Token": gm_csrf},
        json={"action": "HOLD", "note": "GM must not act in DCS Payment.", "expected_version": budget["version"]},
    )
    assert denied.status_code == 403, denied.text
    dcs_csrf = sign_in(client, "dcs")
    held = client.post(
        f"/api/v1/dcs-payments/budget/{budget['id']}/actions",
        headers={"X-CSRF-Token": dcs_csrf},
        json={"action": "HOLD", "note": "DCS is unavailable; bank verification is pending.", "expected_version": budget["version"]},
    )
    assert held.status_code == 200, held.text
    assert held.json()["payment_status"] == "ON_HOLD"
