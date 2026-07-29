from .conftest import sign_in


def create_and_submit_loan_payment(client):
    csrf = sign_in(client, "mich")
    created = client.post(
        "/api/v1/expense-requests",
        headers={"X-CSRF-Token": csrf},
        json={
            "expense_type": "LOAN_PAYMENT",
            "request_date": "2026-07-21",
            "due_date": "2026-07-31",
            "party": "Demo Development Bank",
            "purpose": "July equipment-loan installment",
            "requested_source": "Operating bank account",
            "loan_reference": "DEMO-LOAN-2026-004",
            "principal_amount": "40000.00",
            "interest_amount": "3500.00",
            "penalties_fees_amount": "500.00",
        },
    )
    assert created.status_code == 201, created.text
    expense = created.json()
    assert expense["reference"].startswith("LOAN-2026-")
    assert expense["amount"] == "44000.00"
    assert expense["status"] == "DRAFT"

    submitted = client.post(
        f"/api/v1/expense-requests/{expense['id']}/submit",
        params={"expected_version": expense["version"]},
        headers={"X-CSRF-Token": csrf},
    )
    assert submitted.status_code == 200, submitted.text
    return submitted.json()


def test_loan_payment_ends_at_dcs_payment_until_accounting_role_is_defined(client):
    expense = create_and_submit_loan_payment(client)

    gm_csrf = sign_in(client, "gm")
    approved = client.post(
        f"/api/v1/expense-requests/{expense['id']}/approve",
        headers={"X-CSRF-Token": gm_csrf},
        json={"expected_version": expense["version"], "reason": "Scheduled obligation verified"},
    )
    assert approved.status_code == 200, approved.text
    expense = approved.json()
    assert expense["status"] == "APPROVED"

    dcs_csrf = sign_in(client, "dcs")
    disbursed = client.post(
        f"/api/v1/expense-requests/{expense['id']}/disburse",
        headers={"X-CSRF-Token": dcs_csrf},
        json={
            "mode": "Bank transfer",
            "source": "Operating bank account",
            "paid_to": "Demo Development Bank",
            "transaction_reference": "DEMO-BANK-LOAN-0001",
            "expected_version": expense["version"],
        },
    )
    assert disbursed.status_code == 200, disbursed.text
    expense = disbursed.json()
    assert expense["status"] == "DISBURSED"
    assert expense["disbursement"]["amount"] == "44000.00"


def test_requester_cannot_approve_loan_payment(client):
    expense = create_and_submit_loan_payment(client)
    requester_csrf = sign_in(client, "requester")
    response = client.post(
        f"/api/v1/expense-requests/{expense['id']}/approve",
        headers={"X-CSRF-Token": requester_csrf},
        json={"expected_version": expense["version"]},
    )
    assert response.status_code == 403


def test_admin_superuser_can_approve_and_disburse_loan_payment(client):
    expense = create_and_submit_loan_payment(client)
    admin_csrf = sign_in(client, "admin")
    admin_id = client.get("/api/v1/auth/me").json()["id"]
    approved = client.post(
        f"/api/v1/expense-requests/{expense['id']}/approve",
        headers={"X-CSRF-Token": admin_csrf},
        json={"expected_version": expense["version"], "reason": "Administrator superuser approval"},
    )
    assert approved.status_code == 200, approved.text
    expense = approved.json()
    disbursed = client.post(
        f"/api/v1/expense-requests/{expense['id']}/disburse",
        headers={"X-CSRF-Token": admin_csrf},
        json={
            "mode": "Bank transfer",
            "source": "Operating bank account",
            "paid_to": "Demo Development Bank",
            "transaction_reference": "DEMO-ADMIN-SUPERUSER-LOAN-0001",
            "expected_version": expense["version"],
        },
    )
    assert disbursed.status_code == 200, disbursed.text
    assert disbursed.json()["disbursement"]["disbursed_by_id"] == admin_id


def test_loan_total_must_match_visible_breakdown(client):
    csrf = sign_in(client, "mich")
    response = client.post(
        "/api/v1/expense-requests",
        headers={"X-CSRF-Token": csrf},
        json={
            "expense_type": "LOAN_PAYMENT",
            "request_date": "2026-07-21",
            "due_date": "2026-07-31",
            "party": "Demo Development Bank",
            "purpose": "July installment",
            "requested_source": "Operating bank account",
            "loan_reference": "DEMO-LOAN-2026-004",
            "principal_amount": "40000.00",
            "interest_amount": "3500.00",
            "penalties_fees_amount": "500.00",
            "amount": "45000.00",
        },
    )
    assert response.status_code == 422


def test_other_request_for_payment_has_generic_reference_and_no_funding_source(client):
    csrf = sign_in(client, "mich")
    response = client.post(
        "/api/v1/expense-requests",
        headers={"X-CSRF-Token": csrf},
        json={
            "expense_type": "OTHER",
            "request_date": "2026-07-22",
            "party": "Demo Compliance Vendor",
            "purpose": "One-time permit filing outside regular OPEX categories",
            "amount": "1750.00",
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["reference"].startswith("RFP-2026-")
    assert response.json()["requested_source"] is None


def test_management_dashboard_summarizes_monthly_request_for_payment_by_type(client):
    csrf = sign_in(client, "mich")
    payloads = [
        {"expense_type": "OPEX", "party": "Office Landlord", "purpose": "Monthly office rent", "amount": "30000.00"},
        {"expense_type": "MARKETING", "party": "Trade Publisher", "purpose": "Campaign placement", "amount": "12000.00"},
        {
            "expense_type": "LOAN_PAYMENT",
            "party": "Demo Development Bank",
            "purpose": "Equipment loan",
            "loan_reference": "LOAN-JULY",
            "due_date": "2026-07-31",
            "requested_source": "Operating bank account",
            "principal_amount": "40000.00",
            "interest_amount": "3000.00",
            "penalties_fees_amount": "0.00",
        },
        {"expense_type": "OTHER", "party": "Permit Office", "purpose": "One-time permit", "amount": "1500.00"},
    ]
    for payload in payloads:
        response = client.post(
            "/api/v1/expense-requests",
            headers={"X-CSRF-Token": csrf},
            json={"request_date": "2026-07-22", **payload},
        )
        assert response.status_code == 201, response.text

    sign_in(client, "admin")
    dashboard = client.get("/api/v1/dashboard/shipment-profitability?month=2026-07")
    assert dashboard.status_code == 200, dashboard.text
    summary = dashboard.json()["request_for_payment_summary"]
    assert summary == {
        "month": "2026-07",
        "opex_total": "30000.00",
        "marketing_total": "12000.00",
        "loan_payment_total": "43000.00",
        "other_total": "1500.00",
        "grand_total": "86500.00",
        "opex_count": 1,
        "marketing_count": 1,
        "loan_payment_count": 1,
        "other_count": 1,
        "total_count": 4,
    }

    sign_in(client, "mich")
    private_dashboard = client.get("/api/v1/dashboard/shipment-profitability?month=2026-07")
    assert private_dashboard.status_code == 200
    assert private_dashboard.json()["request_for_payment_summary"] is None


def test_dashboard_rejects_invalid_month(client):
    sign_in(client, "gm")
    response = client.get("/api/v1/dashboard/shipment-profitability?month=2026-13")
    assert response.status_code == 422
