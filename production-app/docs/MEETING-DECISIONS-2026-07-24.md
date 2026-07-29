# PIMASCOR Meeting Decisions — 24 July 2026

This is the implementation checklist extracted from the 109-minute operational
dashboard evaluation in `Operational Dashboard and Accounting Progress
Meeting.md`. It is the controlling product record when it conflicts with an
earlier prototype note.

## Confirmed PIMASCOR workflow

1. A Sales Executive or authorized Requester prepares a client quotation.
2. The GM approves or returns the quotation. DCS can see it and may use a
   reasoned, audited override only when the normal approver is unavailable.
3. The client-accepted quotation and its terms are the shipment contract. A
   signed/scanned copy must remain linked to the shipment.
4. The processor creates a Budget Request from that accepted quotation.
5. Mich reviews the processor's initial entry before the GM can decide it.
6. The GM approves, rejects, or returns the reviewed request. DCS has concurrent
   visibility and exceptional, reasoned override authority.
7. Approved Budget, OPEX, Marketing, Loan Payment, and Other requests appear in
   **DCS for Payment**.
8. DCS selects an Administrator-configured, masked funding source, records the
   actual payment reference, and attaches proof of payment.
9. The Requester sees the attributable progress states without receiving access
   to the DCS payment workspace or confidential payment evidence.
10. After payment, the Requester records actual expenses and receipts and
    submits the Liquidation.
11. Mich receives a separate Liquidation review task, checks digital evidence
    and confirms possession of original physical receipts. A variance cannot be
    closed without the matching return or reimbursement proof.
12. Mich prepares Billing, the GM approves or returns it, and Mich finalizes the
    approved document. Finalization locks the record.
13. Replacement Billing, Credit Memo, and void proposals never overwrite the
    original and require GM approval. The Budget, payment, and Liquidation trail
    remains unchanged.
14. Client payments can be allocated across one or more finalized SOAs. The
    system derives unapplied, partial, or full allocation and collection state.
    A check number is sufficient identification for a check; users do not
    repeat it in a separate reference field.

## Required visibility and controls

- The GM's primary screen is Shipment Profitability, with reporting month,
  shipment state, selling, actual spending, profit, margin, Liquidation,
  collection, aging, and work awaiting action.
- Management can identify Not Billed, Billed, Unpaid, Partially Collected, Fully
  Collected, Liquidation Not Started, Liquidation Pending, and Liquidated work.
- DCS can pay, hold, return, resume, and annotate a payable. Payment sources show
  a bank name/currency and masked last four digits, never a full account number.
- Source documents, shipment references, sequential Billing references,
  documents, and audit events remain searchable and linked.
- Application audit events must identify the actor, action, record, time,
  outcome/reason, and correlation identifier without storing secrets.
- Operational records are prepared for independent accounting review and later
  QuickBooks transfer. The dashboard does not claim to replace the accounting
  ledger or to have live QuickBooks integration.

## Explicit scope boundaries

- Native App Store and Play Store applications, automated QuickBooks
  integration, and an on-premises NAS mirror are follow-up deployment projects.
  The current deliverable remains a responsive cross-browser PWA with private
  object storage.
- AccuStandard inventory, Padang project accounting, and Lemans job/material
  tracking are separate applications and are not PIMASCOR modules.
