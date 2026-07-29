from .conftest import review_budget, sign_in


def test_budget_create_submit_approve_and_release(client):
    csrf = sign_in(client)
    headers = {"X-CSRF-Token": csrf}
    clients = client.get("/api/v1/clients").json()

    created = client.post(
        "/api/v1/budget-requests",
        headers=headers,
        json={
            "client_id": clients[0]["id"],
            "shipment_reference": "MNL-TEST-001",
            "request_date": "2026-07-20",
            "currency": "PHP",
            "items": [
                {"kind": "BUYING", "description": "Port charges", "amount": "50000.00"},
                {"kind": "SELLING", "description": "Client charge", "amount": "65000.00"},
            ],
        },
    )
    assert created.status_code == 201, created.text
    budget = created.json()
    assert budget["buying_total"] == "50000.00"

    submitted = client.post(
        f"/api/v1/budget-requests/{budget['id']}/submit",
        params={"expected_version": budget["version"]},
        headers=headers,
    )
    assert submitted.status_code == 200, submitted.text
    budget = submitted.json()
    assert budget["status"] == "PENDING_REVIEW"
    budget = review_budget(client, budget)
    assert budget["status"] == "PENDING_APPROVAL"
    headers = {"X-CSRF-Token": sign_in(client, "admin")}

    approved = client.post(
        f"/api/v1/approvals/{budget['id']}/approve",
        headers=headers,
        json={"expected_version": budget["version"], "reason": "Administrator superuser approval"},
    )
    assert approved.status_code == 200, approved.text
    budget = approved.json()
    assert budget["status"] == "APPROVED"

    headers = {"X-CSRF-Token": sign_in(client, "admin")}
    released = client.post(
        f"/api/v1/budget-requests/{budget['id']}/releases",
        headers=headers,
        json={
                "amount": "50000.00",
                "mode": "Bank transfer",
                "source": "BDO Operating Account",
                "recipient": "Port operator",
                "transaction_reference": "BANK-TEST-001",
                "paid_on": "2026-07-20",
                "expected_version": budget["version"],
        },
    )
    assert released.status_code == 201, released.text
    assert released.json()["amount"] == "50000.00"
    assert released.json()["source"] == "BDO Operating Account"


def test_release_cannot_exceed_approved_buying_total(client):
    csrf = sign_in(client)
    headers = {"X-CSRF-Token": csrf}
    clients = client.get("/api/v1/clients").json()
    created = client.post(
        "/api/v1/budget-requests",
        headers=headers,
        json={
            "client_id": clients[0]["id"],
            "shipment_reference": "MNL-LIMIT-001",
            "request_date": "2026-07-20",
            "items": [{"kind": "BUYING", "description": "Handling", "amount": "100.00"}],
        },
    ).json()
    submitted = client.post(
        f"/api/v1/budget-requests/{created['id']}/submit",
        params={"expected_version": created["version"]},
        headers=headers,
    ).json()
    submitted = review_budget(client, submitted)
    gm_headers = {"X-CSRF-Token": sign_in(client, "gm")}
    approved = client.post(
        f"/api/v1/approvals/{created['id']}/approve",
        headers=gm_headers,
        json={"expected_version": submitted["version"]},
    ).json()
    headers = {"X-CSRF-Token": sign_in(client, "admin")}
    response = client.post(
        f"/api/v1/budget-requests/{created['id']}/releases",
        headers=headers,
        json={
            "amount": "101.00",
            "mode": "Cash",
            "recipient": "Operator",
            "transaction_reference": "BANK-TEST-002",
            "expected_version": approved["version"],
        },
    )
    assert response.status_code == 422


def test_requester_can_edit_only_an_own_unsubmitted_budget_draft(client):
    requester_headers = {"X-CSRF-Token": sign_in(client, "requester")}
    available_clients = client.get("/api/v1/clients").json()
    created = client.post(
        "/api/v1/budget-requests",
        headers=requester_headers,
        json={
            "client_id": available_clients[0]["id"],
            "shipment_reference": "MNL-DRAFT-EDIT-001",
            "request_date": "2026-07-20",
            "currency": "PHP",
            "notes": "Initial draft",
            "items": [
                {"kind": "BUYING", "description": "Handling", "amount": "100.00"},
                {"kind": "SELLING", "description": "Handling", "amount": "150.00"},
            ],
        },
    ).json()

    updated = client.patch(
        f"/api/v1/budget-requests/{created['id']}",
        headers=requester_headers,
        json={
            "expected_version": created["version"],
            "client_id": available_clients[0]["id"],
            "shipment_reference": "MNL-DRAFT-EDIT-002",
            "request_date": "2026-07-21",
            "currency": "PHP",
            "notes": "Corrected before submission",
            "items": [
                {"kind": "BUYING", "description": "Handling", "amount": "125.00"},
                {"kind": "SELLING", "description": "Handling", "amount": "200.00"},
            ],
        },
    )
    assert updated.status_code == 200, updated.text
    draft = updated.json()
    assert draft["shipment_reference"] == "MNL-DRAFT-EDIT-002"
    assert draft["buying_total"] == "125.00"
    assert draft["selling_total"] == "200.00"
    assert draft["version"] == created["version"] + 1

    submitted = client.post(
        f"/api/v1/budget-requests/{draft['id']}/submit",
        params={"expected_version": draft["version"]},
        headers=requester_headers,
    ).json()
    locked = client.patch(
        f"/api/v1/budget-requests/{draft['id']}",
        headers=requester_headers,
        json={
            "expected_version": submitted["version"],
            "client_id": available_clients[0]["id"],
            "shipment_reference": "MNL-DRAFT-EDIT-003",
            "request_date": "2026-07-21",
            "currency": "PHP",
            "items": [{"kind": "BUYING", "description": "Handling", "amount": "125.00"}],
        },
    )
    assert locked.status_code == 409

    gm_headers = {"X-CSRF-Token": sign_in(client, "gm")}
    forbidden = client.patch(
        f"/api/v1/budget-requests/{draft['id']}",
        headers=gm_headers,
        json={
            "expected_version": submitted["version"],
            "client_id": available_clients[0]["id"],
            "shipment_reference": "MNL-DRAFT-EDIT-004",
            "request_date": "2026-07-21",
            "currency": "PHP",
            "items": [{"kind": "BUYING", "description": "Handling", "amount": "125.00"}],
        },
    )
    assert forbidden.status_code == 403
