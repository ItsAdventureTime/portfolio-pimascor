from .conftest import review_budget, sign_in


def approved_budget(client):
    requester_csrf = sign_in(client, "requester")
    client_id = client.get("/api/v1/clients").json()[0]["id"]
    created = client.post(
        "/api/v1/budget-requests",
        headers={"X-CSRF-Token": requester_csrf},
        json={
            "client_id": client_id,
            "shipment_reference": "OPS-WORKFLOW-SHIPMENT",
            "request_date": "2026-07-22",
            "currency": "PHP",
            "items": [
                {
                    "kind": "BUYING",
                    "classification": "PASS_THROUGH",
                    "description": "Port and handling costs",
                    "amount": "50000.00",
                },
                {
                    "kind": "SELLING",
                    "classification": "PASS_THROUGH",
                    "description": "Client pass-through costs",
                    "amount": "50000.00",
                },
                {
                    "kind": "SELLING",
                    "classification": "SERVICE_CHARGE",
                    "description": "Coordination service charge",
                    "amount": "10000.00",
                },
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
    approved = client.post(
        f"/api/v1/approvals/{created['id']}/approve",
        headers={"X-CSRF-Token": gm_csrf},
        json={"expected_version": submitted["version"], "reason": "Reviewed"},
    )
    assert approved.status_code == 200, approved.text
    return approved.json(), client_id


def test_liquidation_requires_requester_receipt_and_mich_variance_proof(client, monkeypatch):
    monkeypatch.setattr("pimascor_api.routers.operations.put_document", lambda **_: None)
    budget, _ = approved_budget(client)
    dcs_csrf = sign_in(client, "dcs")
    paid = client.post(
        f"/api/v1/dcs-payments/budget/{budget['id']}/pay",
        headers={"X-CSRF-Token": dcs_csrf},
        json={
            "amount": "50000.00",
            "paid_on": "2026-07-22",
            "mode": "Bank transfer",
            "source": "Operating bank account",
            "recipient": "Port operator",
            "transaction_reference": "OPS-LIQ-001",
            "expected_version": budget["version"],
        },
    )
    assert paid.status_code == 200, paid.text

    requester_csrf = sign_in(client, "requester")
    draft = client.post(
        f"/api/v1/liquidations/budget/{budget['id']}",
        headers={"X-CSRF-Token": requester_csrf},
        json={
            "lines": [{"description": "Actual port and handling", "amount": "48000.00"}],
            "evidence": [],
        },
    )
    assert draft.status_code == 200, draft.text
    receipt = client.post(
        f"/api/v1/liquidations/{draft.json()['id']}/evidence",
        headers={"X-CSRF-Token": requester_csrf},
        data={
            "expected_version": str(draft.json()["version"]),
            "kind": "RECEIPT",
        },
        files={"document": ("port-receipt.pdf", b"%PDF-1.4\nsynthetic receipt", "application/pdf")},
    )
    assert receipt.status_code == 200, receipt.text
    submitted = client.post(
        f"/api/v1/liquidations/{draft.json()['id']}/submit",
        params={"expected_version": receipt.json()["version"]},
        headers={"X-CSRF-Token": requester_csrf},
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "PENDING_VARIANCE"

    mich_csrf = sign_in(client, "mich")
    premature = client.post(
        f"/api/v1/liquidations/{submitted.json()['id']}/close",
        headers={"X-CSRF-Token": mich_csrf},
        json={"expected_version": submitted.json()["version"], "note": "Checked", "originals_received_confirmed": True},
    )
    assert premature.status_code == 422

    proof = client.post(
        f"/api/v1/liquidations/{submitted.json()['id']}/evidence",
        headers={"X-CSRF-Token": mich_csrf},
        data={
            "kind": "RETURN_PROOF",
            "expected_version": str(submitted.json()["version"]),
        },
        files={"document": ("returned-funds.pdf", b"%PDF-1.4\nsynthetic proof", "application/pdf")},
    )
    assert proof.status_code == 200, proof.text
    closed = client.post(
        f"/api/v1/liquidations/{proof.json()['id']}/close",
        headers={"X-CSRF-Token": mich_csrf},
        json={"expected_version": proof.json()["version"], "note": "Return verified", "originals_received_confirmed": True},
    )
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "CLOSED"


def test_dashboard_calculates_profitability_from_budget_and_liquidation(client):
    budget, _ = approved_budget(client)
    dcs_csrf = sign_in(client, "dcs")
    paid = client.post(
        f"/api/v1/dcs-payments/budget/{budget['id']}/pay",
        headers={"X-CSRF-Token": dcs_csrf},
        json={
            "amount": "50000.00",
            "paid_on": "2026-07-22",
            "mode": "Bank transfer",
            "source": "Operating bank account",
            "recipient": "Port operator",
            "transaction_reference": "DASHBOARD-PROFIT-001",
            "expected_version": budget["version"],
        },
    )
    assert paid.status_code == 200, paid.text
    requester_csrf = sign_in(client, "requester")
    liquidation = client.post(
        f"/api/v1/liquidations/budget/{budget['id']}",
        headers={"X-CSRF-Token": requester_csrf},
        json={"lines": [{"description": "Actual shipment spending", "amount": "48000.00"}]},
    )
    assert liquidation.status_code == 200, liquidation.text
    dashboard = client.get("/api/v1/dashboard/shipment-profitability")
    assert dashboard.status_code == 200, dashboard.text
    row = next(item for item in dashboard.json()["rows"] if item["budget_request_id"] == budget["id"])
    assert row["selling_amount"] == "60000.00"
    assert row["actual_spending"] == "48000.00"
    assert row["profit"] == "12000.00"
    assert row["profit_margin_percentage"] == "20.00"
    assert row["collection_status"] == "Not billed"


def test_billing_requires_gm_approval_before_finalize_then_is_immutable_and_collectible(client):
    budget, client_id = approved_budget(client)
    mich_csrf = sign_in(client, "mich")
    draft = client.post(
        f"/api/v1/billing/budget/{budget['id']}",
        headers={"X-CSRF-Token": mich_csrf},
        json={
            "issue_date": "2026-07-22",
            "due_date": "2026-08-21",
            "vat_amount": "0.00",
            "withholding_amount": "0.00",
            "lines": [
                {"description": "Pass-through costs", "classification": "PASS_THROUGH", "amount": "50000.00"},
                {"description": "Service charge", "classification": "SERVICE_CHARGE", "amount": "10000.00"},
            ],
        },
    )
    assert draft.status_code == 201, draft.text
    assert draft.json()["vat_amount"] == "1200.00"
    assert draft.json()["withholding_amount"] == "200.00"
    assert draft.json()["net_due"] == "61000.00"
    premature = client.post(
        f"/api/v1/billing/{draft.json()['id']}/finalize",
        headers={"X-CSRF-Token": mich_csrf},
        json={"expected_version": draft.json()["version"], "confirmation": "FINALIZE"},
    )
    assert premature.status_code == 409
    submitted = client.post(
        f"/api/v1/billing/{draft.json()['id']}/submit",
        headers={"X-CSRF-Token": mich_csrf},
        json={"expected_version": draft.json()["version"]},
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "PENDING_APPROVAL"

    admin_csrf = sign_in(client, "admin")
    approved = client.post(
        f"/api/v1/billing/{draft.json()['id']}/decision",
        headers={"X-CSRF-Token": admin_csrf},
        json={"expected_version": submitted.json()["version"], "approve": True},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "APPROVED"
    assert approved.json()["approved_by"]["role"] == "ADMIN"

    mich_csrf = sign_in(client, "mich")
    finalized = client.post(
        f"/api/v1/billing/{draft.json()['id']}/finalize",
        headers={"X-CSRF-Token": mich_csrf},
        json={"expected_version": approved.json()["version"], "confirmation": "FINALIZE"},
    )
    assert finalized.status_code == 200, finalized.text

    replacement = client.post(
        f"/api/v1/billing/{finalized.json()['id']}/replacement",
        headers={"X-CSRF-Token": mich_csrf},
        json={
            "expected_version": finalized.json()["version"],
            "reason": "Client address correction",
            "issue_date": "2026-07-23",
            "due_date": "2026-08-22",
            "lines": [
                {"description": "Pass-through costs", "classification": "PASS_THROUGH", "amount": "50000.00"},
                {"description": "Service charge", "classification": "SERVICE_CHARGE", "amount": "10000.00"},
            ],
        },
    )
    assert replacement.status_code == 201, replacement.text
    assert replacement.json()["status"] == "PENDING_APPROVAL"
    assert replacement.json()["reference"].startswith("RPL-PROP-")
    gm_csrf = sign_in(client, "gm")
    approved_replacement = client.post(
        f"/api/v1/billing/{replacement.json()['id']}/decision",
        headers={"X-CSRF-Token": gm_csrf},
        json={"expected_version": replacement.json()["version"], "approve": True},
    )
    assert approved_replacement.status_code == 200, approved_replacement.text
    assert approved_replacement.json()["reference"].endswith("-R1")
    mich_csrf = sign_in(client, "mich")
    blocked_replacement = client.post(
        f"/api/v1/billing/{replacement.json()['id']}/finalize",
        headers={"X-CSRF-Token": mich_csrf},
        json={"expected_version": approved_replacement.json()["version"], "confirmation": "FINALIZE"},
    )
    assert blocked_replacement.status_code == 409

    immutable = client.patch(
        f"/api/v1/billing/{finalized.json()['id']}",
        headers={"X-CSRF-Token": mich_csrf},
        json={
            "expected_version": finalized.json()["version"],
            "issue_date": "2026-07-22",
            "due_date": "2026-08-21",
            "vat_amount": "0.00",
            "withholding_amount": "0.00",
            "lines": [{"description": "Changed total", "classification": "SERVICE_CHARGE", "amount": "1.00"}],
        },
    )
    assert immutable.status_code == 409

    payment = client.post(
        "/api/v1/client-payments",
        headers={"X-CSRF-Token": mich_csrf},
        json={
            "client_id": client_id,
            "payment_method": "CHECK",
            "check_number": "CHK-000031",
            "check_list_number": "3",
            "receiving_bank": "Operating bank account",
            "payment_date": "2026-07-22",
            "amount": "25000.00",
            "allocations": [{"billing_id": finalized.json()["id"], "amount": "25000.00"}],
        },
    )
    assert payment.status_code == 201, payment.text
    register = client.get("/api/v1/client-payments")
    assert register.status_code == 200, register.text
    assert register.json()[0]["check_number"] == "CHK-000031"
    assert register.json()[0]["payment_reference"] == "CHECK-CHK-000031"
    receivables = client.get("/api/v1/receivables")
    row = next(item for item in receivables.json() if item["id"] == finalized.json()["id"])
    assert row["collection_status"] == "Partially Collected"
    assert row["remaining_amount"] == "36000.00"

    credit = client.post(
        f"/api/v1/billing/{finalized.json()['id']}/credit-memos",
        headers={"X-CSRF-Token": mich_csrf},
        json={"reason": "Approved client adjustment", "amount": "5000.00", "submit_for_approval": True},
    )
    assert credit.status_code == 201, credit.text
    admin_csrf = sign_in(client, "admin")
    approved_credit = client.post(
        f"/api/v1/credit-memos/{credit.json()['id']}/decision",
        headers={"X-CSRF-Token": admin_csrf},
        json={"expected_version": credit.json()["version"], "approve": True},
    )
    assert approved_credit.status_code == 200, approved_credit.text
    adjusted = client.get("/api/v1/receivables")
    adjusted_row = next(item for item in adjusted.json() if item["id"] == finalized.json()["id"])
    assert adjusted_row["approved_credit_memo_amount"] == "5000.00"
    assert adjusted_row["remaining_amount"] == "31000.00"

    gm_csrf = sign_in(client, "gm")
    forbidden = client.post(
        f"/api/v1/billing/{finalized.json()['id']}/void",
        headers={"X-CSRF-Token": gm_csrf},
        json={"expected_version": finalized.json()["version"], "reason": "Not permitted"},
    )
    assert forbidden.status_code == 403
