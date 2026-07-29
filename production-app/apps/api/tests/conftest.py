import os

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from pimascor_api.db import Base, get_db
from pimascor_api.main import app
from decimal import Decimal

from pimascor_api.models import Client, FinancialClassification, FundingSource, Role, TaxProfile, User
from pimascor_api.security import hash_password


test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)


def override_db():
    with TestingSession() as db:
        yield db


app.dependency_overrides[get_db] = override_db


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    with TestingSession() as db:
        db.add_all(
            [
                User(
                    username="admin",
                    email="admin@example.com",
                    display_name="Admin User",
                    password_hash=hash_password("Correct-Horse-123!"),
                    role=Role.ADMIN,
                ),
                User(
                    username="requester",
                    email="requester@example.com",
                    display_name="Request User",
                    password_hash=hash_password("Correct-Horse-123!"),
                    role=Role.REQUESTER,
                ),
                User(
                    username="gm",
                    email="gm@example.com",
                    display_name="GM User",
                    password_hash=hash_password("Correct-Horse-123!"),
                    role=Role.GM,
                ),
                User(
                    username="dcs",
                    email="dcs@example.com",
                    display_name="DCS User",
                    password_hash=hash_password("Correct-Horse-123!"),
                    role=Role.DCS,
                ),
                User(
                    username="mich",
                    email="mich@example.com",
                    display_name="Mich User",
                    password_hash=hash_password("Correct-Horse-123!"),
                    role=Role.MICH,
                ),
                Client(code="ACME", name="Acme Shipping"),
                FundingSource(name="Operating bank account", active=True),
                TaxProfile(
                    name="Standard service",
                    classification=FinancialClassification.SERVICE_CHARGE,
                    vat_rate=Decimal("0.120000"),
                    withholding_rate=Decimal("0.020000"),
                    active=True,
                ),
                TaxProfile(
                    name="Pass-through",
                    classification=FinancialClassification.PASS_THROUGH,
                    vat_rate=Decimal("0.000000"),
                    withholding_rate=Decimal("0.000000"),
                    active=True,
                ),
            ]
        )
        db.commit()
    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def sign_in(client: TestClient, username: str = "admin") -> str:
    started = client.post(
        "/api/v1/auth/password/start",
        json={"username": username, "password": "Correct-Horse-123!"},
    )
    assert started.status_code == 200, started.text
    body = started.json()
    verified = client.post(
        "/api/v1/auth/email-code/verify",
        json={"challenge_id": body["challenge_id"], "code": body["development_code"]},
    )
    assert verified.status_code == 200, verified.text
    return verified.json()["csrf_token"]


def review_budget(client: TestClient, submitted: dict) -> dict:
    csrf = sign_in(client, "mich")
    response = client.post(
        f"/api/v1/budget-reviews/{submitted['id']}/review",
        headers={"X-CSRF-Token": csrf},
        json={"expected_version": submitted["version"], "reason": "Initial entry verified"},
    )
    assert response.status_code == 200, response.text
    return response.json()
