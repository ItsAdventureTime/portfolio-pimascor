from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import delete, select

from .config import get_settings
from .db import SessionLocal
from .models import (
    ApprovalDecision,
    AuditEvent,
    Billing,
    BillingLine,
    BillingStatus,
    BudgetKind,
    BudgetItem,
    BudgetRequest,
    BudgetStatus,
    BudgetSubmission,
    Client,
    ClientPayment,
    CreditMemo,
    EmailChallenge,
    ExpenseDecision,
    ExpenseDisbursement,
    ExpenseRequest,
    ExpenseStatus,
    ExpenseType,
    ExpenseValidation,
    EvidenceKind,
    FinancialClassification,
    FundingSource,
    ItemKind,
    IncidentReport,
    LoginSession,
    Liquidation,
    LiquidationEvidence,
    LiquidationLine,
    LiquidationStatus,
    PaymentAllocation,
    PaymentAnnotation,
    PaymentStatus,
    Release,
    QuotationStatus,
    Role,
    SalesQuotation,
    SalesQuotationLine,
    SupportTicket,
    SupportTicketReply,
    TaxProfile,
    User,
    UserStatus,
    utc_now,
)
from .services.storage import delete_demo_documents


def role_user(db, role: Role) -> User:
    user = db.scalar(
        select(User).where(User.role == role, User.status == UserStatus.ACTIVE).order_by(User.created_at)
    )
    if user is None:
        raise SystemExit(
            f"Demo reset requires at least one active {role.value} account. Create demo users first."
        )
    return user


def add_expense(
    db,
    *,
    reference: str,
    expense_type: ExpenseType,
    requester: User,
    party: str,
    purpose: str,
    amount: Decimal,
    status: ExpenseStatus,
    gm: User,
    dcs: User,
    mich: User,
    principal: Decimal = Decimal("0.00"),
    interest: Decimal = Decimal("0.00"),
    fees: Decimal = Decimal("0.00"),
    loan_reference: str | None = None,
    due_date: date | None = None,
) -> ExpenseRequest:
    request = ExpenseRequest(
        reference=reference,
        expense_type=expense_type,
        requester_id=requester.id,
        request_date=date.today(),
        due_date=due_date,
        party=party,
        purpose=purpose,
        requested_source=None,
        loan_reference=loan_reference,
        principal_amount=principal,
        interest_amount=interest,
        penalties_fees_amount=fees,
        amount=amount,
        status=status,
        payment_status=(
            PaymentStatus.PAID
            if status in (ExpenseStatus.DISBURSED, ExpenseStatus.PENDING_VALIDATION, ExpenseStatus.VALIDATED)
            else PaymentStatus.PENDING
            if status == ExpenseStatus.APPROVED
            else PaymentStatus.NOT_READY
        ),
        version=1,
    )
    if status not in (ExpenseStatus.DRAFT, ExpenseStatus.PENDING_APPROVAL, ExpenseStatus.REJECTED):
        request.decisions.append(
            ExpenseDecision(actor_user_id=gm.id, outcome="APPROVED", reason="Synthetic demo approval")
        )
    if status in (ExpenseStatus.DISBURSED, ExpenseStatus.PENDING_VALIDATION, ExpenseStatus.VALIDATED):
        request.disbursement = ExpenseDisbursement(
            amount=amount,
            mode="Bank transfer",
            source="Demo operating account",
            paid_to=party,
            transaction_reference=f"DEMO-TXN-{reference}",
            disbursed_by_id=dcs.id,
        )
    if status == ExpenseStatus.VALIDATED:
        request.validation = ExpenseValidation(
            validated_by_id=mich.id,
            notes="Synthetic payment proof and schedule matched",
        )
    db.add(request)
    return request


def reset_demo() -> None:
    settings = get_settings()
    if settings.deployment_tier != "demo":
        raise SystemExit("Refusing to reset: DEPLOYMENT_TIER must be exactly 'demo'.")

    # The demo is disposable. Remove its object prefix before replacing the
    # database baseline so uploads cannot survive as unreferenced private files.
    delete_demo_documents()

    with SessionLocal.begin() as db:
        role_user(db, Role.ADMIN)
        requester = role_user(db, Role.REQUESTER)
        gm = role_user(db, Role.GM)
        dcs = role_user(db, Role.DCS)
        mich = role_user(db, Role.MICH)

        for model in (
            SupportTicketReply,
            SupportTicket,
            IncidentReport,
            CreditMemo,
            PaymentAllocation,
            ClientPayment,
            BillingLine,
            Billing,
            LiquidationEvidence,
            LiquidationLine,
            Liquidation,
            PaymentAnnotation,
            ExpenseValidation,
            ExpenseDisbursement,
            ExpenseDecision,
            ExpenseRequest,
            Release,
            ApprovalDecision,
            BudgetSubmission,
            BudgetItem,
            BudgetRequest,
            SalesQuotationLine,
            SalesQuotation,
            AuditEvent,
            EmailChallenge,
            LoginSession,
            FundingSource,
            TaxProfile,
            Client,
        ):
            db.execute(delete(model))

        clients = [
            Client(code="DEMO-ACT", name="Demo Archipelago Cargo Trading"),
            Client(code="DEMO-HFI", name="Demo Harborline Foods Inc."),
            Client(code="DEMO-PBW", name="Demo Pacific Buildworks"),
        ]
        db.add_all(clients)
        db.add_all(
            [
                FundingSource(name="Bank of PIMASCOR", active=True),
                FundingSource(name="Advances to DCS", active=True),
            ]
        )
        db.add_all(
            [
                TaxProfile(
                    name="Demo standard service charge",
                    classification=FinancialClassification.SERVICE_CHARGE,
                    vat_rate=Decimal("0.120000"),
                    withholding_rate=Decimal("0.020000"),
                    active=True,
                ),
                TaxProfile(
                    name="Demo pass-through cost",
                    classification=FinancialClassification.PASS_THROUGH,
                    vat_rate=Decimal("0.000000"),
                    withholding_rate=Decimal("0.000000"),
                    active=True,
                ),
            ]
        )
        db.flush()

        budgets = [
            ("BR-DEMO-00001", clients[0], "Manila to Davao sample shipment", BudgetStatus.DRAFT, "76300.00", "96360.00"),
            ("BR-DEMO-00002", clients[1], "Cebu to Manila sample reefer service", BudgetStatus.PENDING_REVIEW, "58200.00", "78800.00"),
            ("BR-DEMO-00003", clients[2], "Batangas sample port handling", BudgetStatus.APPROVED, "42600.00", "59000.00"),
        ]
        seeded_budgets: list[BudgetRequest] = []
        for index, (reference, client, shipment, status, buying, selling) in enumerate(budgets, start=1):
            quotation = SalesQuotation(
                reference=f"SQ-DEMO-{index:05d}",
                client_id=client.id,
                shipment_reference=shipment,
                quoted_amount=Decimal(selling),
                terms_and_conditions="Synthetic accepted quotation with standard 30-day payment terms.",
                status=QuotationStatus.CLIENT_ACCEPTED,
                created_by_id=requester.id,
                submitted_at=utc_now(),
                approved_by_id=gm.id,
                approved_at=utc_now(),
                client_accepted_at=date.today(),
                client_signatory="Demo Client Signatory",
                signed_file_name=f"sq-demo-{index:05d}-accepted.pdf",
            )
            db.add(quotation)
            db.flush()
            budget = BudgetRequest(
                reference=reference,
                budget_kind=BudgetKind.MAIN,
                client_id=client.id,
                quotation_id=quotation.id,
                shipment_reference=shipment,
                request_date=date.today(),
                requester_id=requester.id,
                buying_total=Decimal(buying),
                selling_total=Decimal(selling),
                status=status,
                payment_status=(
                    PaymentStatus.PENDING
                    if status == BudgetStatus.APPROVED
                    else PaymentStatus.NOT_READY
                ),
            )
            budget.items = [
                BudgetItem(kind=ItemKind.BUYING, description="Synthetic operating cost", amount=Decimal(buying), sort_order=0),
                BudgetItem(kind=ItemKind.SELLING, description="Synthetic client charge", amount=Decimal(selling), sort_order=1),
            ]
            db.add(budget)
            seeded_budgets.append(budget)
            db.flush()
            if status in (BudgetStatus.PENDING_REVIEW, BudgetStatus.PENDING_APPROVAL, BudgetStatus.APPROVED):
                submission = BudgetSubmission(
                    budget_request_id=budget.id,
                    version=budget.version,
                    submitted_by_id=requester.id,
                )
                db.add(submission)
                db.flush()
                if status == BudgetStatus.APPROVED:
                    db.add(
                        ApprovalDecision(
                            submission_id=submission.id,
                            actor_user_id=gm.id,
                            outcome="APPROVED",
                            reason="Synthetic demo approval",
                        )
                    )

        additional = BudgetRequest(
            reference="ABR-DEMO-00001",
            budget_kind=BudgetKind.ADDITIONAL,
            parent_budget_id=seeded_budgets[2].id,
            additional_reason="Unexpected port storage after a weather delay",
            related_expense_description="Synthetic port storage liquidation expense",
            related_expense_amount=Decimal("13000.00"),
            client_id=seeded_budgets[2].client_id,
            shipment_reference=seeded_budgets[2].shipment_reference,
            request_date=date.today(),
            requester_id=requester.id,
            buying_total=Decimal("13000.00"),
            selling_total=Decimal("0.00"),
            status=BudgetStatus.APPROVED,
            payment_status=PaymentStatus.RETURNED,
        )
        additional.items = [
            BudgetItem(
                kind=ItemKind.BUYING,
                description="Synthetic additional port storage",
                amount=Decimal("13000.00"),
                sort_order=0,
            )
        ]
        db.add(additional)
        db.flush()
        additional_submission = BudgetSubmission(
            budget_request_id=additional.id,
            version=additional.version,
            submitted_by_id=requester.id,
        )
        db.add(additional_submission)
        db.flush()
        db.add(
            ApprovalDecision(
                submission_id=additional_submission.id,
                actor_user_id=gm.id,
                outcome="APPROVED",
                reason="Synthetic additional cost approved",
            )
        )
        db.add(
            PaymentAnnotation(
                budget_request_id=additional.id,
                actor_user_id=dcs.id,
                event_type="RETURN",
                note="Please attach the updated port statement before payment.",
            )
        )

        released_budget = seeded_budgets[2]
        released_budget.released_total = Decimal("42600.00")
        released_budget.status = BudgetStatus.RELEASED
        released_budget.payment_status = PaymentStatus.PAID
        db.add(
            Release(
                budget_request_id=released_budget.id,
                amount=Decimal("42600.00"),
                mode="Bank transfer",
                source="Bank of PIMASCOR",
                recipient=requester.display_name,
                transaction_reference="DEMO-TXN-BR-DEMO-00003",
                released_by_id=dcs.id,
            )
        )
        liquidation = Liquidation(
            budget_request_id=released_budget.id,
            requester_id=requester.id,
            status=LiquidationStatus.PENDING_VARIANCE,
            released_total=Decimal("42600.00"),
            actual_total=Decimal("40100.00"),
            submitted_at=utc_now(),
        )
        liquidation.lines = [
            LiquidationLine(description="Demo port charges", amount=Decimal("25100.00"), sort_order=0),
            LiquidationLine(description="Demo trucking receipt", amount=Decimal("15000.00"), sort_order=1),
        ]
        liquidation.evidence = [
            LiquidationEvidence(
                kind=EvidenceKind.RECEIPT,
                file_name="demo-port-charges-receipt.pdf",
                storage_key="demo/liquidations/receipts/demo-port-charges-receipt.pdf",
                uploaded_by_id=requester.id,
            )
        ]
        db.add(liquidation)

        billing = Billing(
            reference="BILL-DEMO-00001",
            budget_request_id=released_budget.id,
            issue_date=date.today() - timedelta(days=40),
            due_date=date.today() - timedelta(days=10),
            service_subtotal=Decimal("9000.00"),
            pass_through_subtotal=Decimal("50000.00"),
            vat_amount=Decimal("1080.00"),
            withholding_amount=Decimal("180.00"),
            total_amount=Decimal("60080.00"),
            net_due=Decimal("59900.00"),
            status=BillingStatus.FINALIZED,
            prepared_by_id=mich.id,
            submitted_by_id=mich.id,
            submitted_at=utc_now(),
            approved_by_id=gm.id,
            approved_at=utc_now(),
            finalized_by_id=mich.id,
            finalized_at=utc_now(),
        )
        billing.lines = [
            BillingLine(
                description="Demo service charges",
                classification=FinancialClassification.SERVICE_CHARGE,
                amount=Decimal("9000.00"),
                vat_rate=Decimal("0.120000"),
                withholding_rate=Decimal("0.020000"),
                vat_amount=Decimal("1080.00"),
                withholding_amount=Decimal("180.00"),
                sort_order=0,
            ),
            BillingLine(
                description="Demo reimbursable port costs",
                classification=FinancialClassification.PASS_THROUGH,
                amount=Decimal("50000.00"),
                vat_rate=Decimal("0.000000"),
                withholding_rate=Decimal("0.000000"),
                vat_amount=Decimal("0.00"),
                withholding_amount=Decimal("0.00"),
                sort_order=1,
            ),
        ]
        db.add(billing)
        db.flush()
        payment = ClientPayment(
            reference="COL-DEMO-00001",
            client_id=released_budget.client_id,
            payment_reference="DEMO-CHECK-1042",
            receiving_bank="Bank of PIMASCOR",
            payment_method="CHECK",
            check_number="DEMO-CHECK-1042",
            check_list_number="3",
            payment_date=date.today() - timedelta(days=3),
            amount=Decimal("30000.00"),
            recorded_by_id=mich.id,
        )
        payment.allocations = [PaymentAllocation(billing_id=billing.id, amount=Decimal("30000.00"))]
        db.add(payment)

        add_expense(
            db,
            reference="OPEX-DEMO-00001",
            expense_type=ExpenseType.OPEX,
            requester=mich,
            party="Demo Cloud Software PH",
            purpose="Synthetic annual software subscription",
            amount=Decimal("24900.00"),
            status=ExpenseStatus.APPROVED,
            gm=gm,
            dcs=dcs,
            mich=mich,
        )
        add_expense(
            db,
            reference="MKT-DEMO-00001",
            expense_type=ExpenseType.MARKETING,
            requester=mich,
            party="Demo Maritime Expo",
            purpose="Synthetic booth materials and event fees",
            amount=Decimal("48000.00"),
            status=ExpenseStatus.PENDING_APPROVAL,
            gm=gm,
            dcs=dcs,
            mich=mich,
        )
        loan_scenarios = [
            ("LOAN-DEMO-00001", ExpenseStatus.DRAFT, "40000.00", "3500.00", "500.00"),
            ("LOAN-DEMO-00002", ExpenseStatus.PENDING_APPROVAL, "60000.00", "4800.00", "0.00"),
            ("LOAN-DEMO-00003", ExpenseStatus.APPROVED, "70000.00", "2500.00", "0.00"),
            ("LOAN-DEMO-00004", ExpenseStatus.DISBURSED, "28000.00", "3200.00", "650.00"),
            ("LOAN-DEMO-00005", ExpenseStatus.DISBURSED, "35000.00", "2900.00", "0.00"),
        ]
        for reference, status, principal, interest, fees in loan_scenarios:
            principal_value = Decimal(principal)
            interest_value = Decimal(interest)
            fees_value = Decimal(fees)
            add_expense(
                db,
                reference=reference,
                expense_type=ExpenseType.LOAN_PAYMENT,
                requester=mich,
                party="Demo Development Bank",
                purpose="Synthetic equipment-loan installment",
                amount=principal_value + interest_value + fees_value,
                status=status,
                gm=gm,
                dcs=dcs,
                mich=mich,
                principal=principal_value,
                interest=interest_value,
                fees=fees_value,
                loan_reference=f"DEMO-ACCOUNT-{reference[-5:]}",
                due_date=date.today() + timedelta(days=10),
            )

    print("PIMASCOR demo business data reset to the approved synthetic scenario.")


if __name__ == "__main__":
    reset_demo()
