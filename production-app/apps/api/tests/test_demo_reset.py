from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

from pimascor_api import demo_reset
from pimascor_api.models import (
    ApprovalDecision,
    BudgetRequest,
    BudgetStatus,
    BudgetSubmission,
    Client,
    ExpenseRequest,
    ExpenseStatus,
    ExpenseType,
    Role,
    SalesQuotation,
    SalesQuotationLine,
    User,
)

from .conftest import TestingSession


def test_demo_reset_builds_actionable_role_scenarios(monkeypatch):
    monkeypatch.setattr(demo_reset, "SessionLocal", TestingSession)
    monkeypatch.setattr(
        demo_reset,
        "get_settings",
        lambda: SimpleNamespace(deployment_tier="demo"),
    )

    demo_reset.reset_demo()

    with TestingSession() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 5
        assert db.scalar(select(func.count()).select_from(Client)) == 3
        assert db.scalar(select(func.count()).select_from(BudgetRequest)) == 4
        assert db.scalar(select(func.count()).select_from(BudgetSubmission)) == 3
        assert db.scalar(select(func.count()).select_from(ApprovalDecision)) == 2

        pending_budget = db.scalar(
            select(BudgetRequest).where(BudgetRequest.status == BudgetStatus.PENDING_REVIEW)
        )
        assert pending_budget is not None

        loans = db.scalars(
            select(ExpenseRequest).where(ExpenseRequest.expense_type == ExpenseType.LOAN_PAYMENT)
        ).all()
        assert len(loans) == 5
        assert {loan.status for loan in loans} == {
            ExpenseStatus.DRAFT,
            ExpenseStatus.PENDING_APPROVAL,
            ExpenseStatus.APPROVED,
            ExpenseStatus.DISBURSED,
        }
        assert sum(loan.status == ExpenseStatus.DISBURSED for loan in loans) == 2


def test_demo_reset_refuses_non_demo_environment(monkeypatch):
    monkeypatch.setattr(
        demo_reset,
        "get_settings",
        lambda: SimpleNamespace(deployment_tier="production"),
    )

    try:
        demo_reset.reset_demo()
    except SystemExit as exc:
        assert "Refusing to reset" in str(exc)
    else:
        raise AssertionError("Production reset guard did not stop execution")


def test_demo_reset_is_repeatable_and_preserves_accounts(monkeypatch):
    monkeypatch.setattr(demo_reset, "SessionLocal", TestingSession)
    monkeypatch.setattr(
        demo_reset,
        "get_settings",
        lambda: SimpleNamespace(deployment_tier="demo"),
    )

    with TestingSession() as db:
        accounts_before = {
            user.username: (user.id, user.email, user.password_hash, user.role, user.status)
            for user in db.scalars(select(User).order_by(User.username))
        }

    demo_reset.reset_demo()
    demo_reset.reset_demo()

    with TestingSession() as db:
        accounts_after = {
            user.username: (user.id, user.email, user.password_hash, user.role, user.status)
            for user in db.scalars(select(User).order_by(User.username))
        }
        assert accounts_after == accounts_before
        assert db.scalar(select(func.count()).select_from(Client)) == 3
        assert db.scalar(select(func.count()).select_from(BudgetRequest)) == 4


def test_demo_reset_removes_quotation_lines_before_quotations(monkeypatch):
    monkeypatch.setattr(demo_reset, "SessionLocal", TestingSession)
    monkeypatch.setattr(
        demo_reset,
        "get_settings",
        lambda: SimpleNamespace(deployment_tier="demo"),
    )
    with TestingSession.begin() as db:
        requester = db.scalar(select(User).where(User.role == Role.REQUESTER))
        client = db.scalar(select(Client))
        assert requester is not None and client is not None
        quotation = SalesQuotation(
            reference="SQ-RESET-FK-TEST",
            client_id=client.id,
            shipment_reference="FK reset test shipment",
            quoted_amount="100.00",
            currency="PHP",
            terms_and_conditions="Synthetic test terms",
            created_by_id=requester.id,
        )
        quotation.lines.append(
            SalesQuotationLine(
                section="DESTINATION_CLEARANCE",
                description="Test charge",
                currency="PHP",
                amount="100.00",
                billed_by="PIMASCOR",
                position=0,
            )
        )
        db.add(quotation)

    demo_reset.reset_demo()

    with TestingSession() as db:
        assert db.scalar(select(func.count()).select_from(SalesQuotationLine)) == 0
        assert db.scalar(
            select(SalesQuotation).where(SalesQuotation.reference == "SQ-RESET-FK-TEST")
        ) is None


def test_demo_reset_refuses_missing_required_account_before_mutation(monkeypatch):
    monkeypatch.setattr(demo_reset, "SessionLocal", TestingSession)
    monkeypatch.setattr(
        demo_reset,
        "get_settings",
        lambda: SimpleNamespace(deployment_tier="demo"),
    )

    with TestingSession.begin() as db:
        admin = db.scalar(select(User).where(User.role == Role.ADMIN))
        assert admin is not None
        db.delete(admin)

    with pytest.raises(SystemExit, match="active ADMIN account"):
        demo_reset.reset_demo()

    with TestingSession() as db:
        assert db.scalar(select(func.count()).select_from(Client)) == 1
