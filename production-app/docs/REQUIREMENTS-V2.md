# PIMASCOR requirements baseline v2

Status: implementation baseline for the revised demo and future production system  
Reviewed source date: 24 July 2026

Demo-only supersession: `DEMO-BUILD-SOURCE-OF-TRUTH-2026-08-08.md` is the
newer source for the demo entry experience, visible Admin role evaluation, and
demo capability exceptions. This baseline remains the production-oriented
workflow reference where it does not conflict with that newer demo document.

## Authority and interpretation

This baseline reconciles:

1. `01_BRIDGE_Operational_Dashboard_Meeting_AI_Context.md` — evaluation meeting findings.
2. `02_BRIDGE_Access_Workflow_Requirements_AI_Context.md` — post-meeting role and workflow corrections.
3. `context-v2.zip` — screenshots of the legacy Apps Script and revised demo used during the evaluation.
4. `possible-fixes/` — 23 July screenshot set and annotated workflow corrections.
5. `Operational Dashboard and Accounting Progress Meeting.md` — the
   109-minute owner evaluation reviewed on 24 July 2026.

`MEETING-DECISIONS-2026-07-24.md` wins if an older project document disagrees.
The person's name is always **Mich**, never “Mitch.” Items that the source
material explicitly leaves unresolved remain decisions for Bridge PH; the
application must not invent accounting or tax policy.

## Plain-language product model

PIMASCOR is a chain of custody for operational and financial work. A request is the purchase order, approval is the manager's signature, DCS payment is the cashier releasing money, Liquidation is the receipt envelope, Billing is what the client owes, and Client Payments is the cash-receipt ledger. Each stage has a named owner and retains the previous stage's history.

The interface must answer three questions without requiring users to understand the implementation:

- What work can I do here?
- What is waiting for me now?
- What happens after I act?

## Approved navigation language

| User goal | Navigation label | Avoid |
|---|---|---|
| Prepare and approve the client offer | Sales Quotations | Treating an unaccepted quote as a contract |
| Ask for shipment funds | Budget Requests / My Budget Requests | Generic “Requests” |
| Decide submitted requests | Approval | A separate approval page per record type |
| Pay approved requests | DCS for Payment | “Release” when the user means actual payment |
| Account for actual shipment spending | My Liquidations / Liquidations to Review | Hiding it under Budget |
| Ask for a non-shipment payment | Request for Payment | Three disconnected navigation destinations |
| Prepare client charges | Prepare Billing / Billing Records | “Invoice” until legal/tax form is confirmed |
| Record money received from clients | Client Payments | “Collections allocation” as the main label |

OPEX, Marketing, Loan Payment, and Other remain distinct **types** inside Request for Payment. This keeps one familiar entry point while preserving reporting and validation differences.

## Role and permission baseline

Permissions are enforced by the API, not only by hidden navigation.

| Capability | Admin | Requester | GM | DCS / CEO | Mich |
|---|---:|---:|---:|---:|---:|
| Shipment Profitability dashboard | All shipments | Own shipments | All shipments | All shipments | All shipments |
| Create own Budget/Additional Budget | Yes | Yes | No | No | No |
| View all shipment expenses | Yes | Own only | Read | Read | Read |
| Approve/reject submitted requests and Billing | Yes | No | Yes | Emergency override | No |
| Review initial Budget Request entry | Yes | No | No | Read | Yes |
| View consolidated payment queue | Yes | No | Read | Act | Read |
| Choose actual funding source and mark paid | Yes | No | No | Yes | No |
| Enter Liquidation expenses and receipts | Yes | Own only | No | No | No |
| Review evidence and close Liquidation | Yes | No | No | No | Yes |
| Create Request for Payment | Yes | No | No | No | Yes |
| Prepare/submit/finalize approved Billing | Yes | View own final | Approve | Read | Yes |
| Record/allocate Client Payment | Yes | No | Read | Read | Yes |
| Void finalized Billing | Yes | No | No | No | No |
| Accounting workspace | Yes | No | No | No | No |
| Bridge PH Activity Monitor | Yes | No | No | No | No |

The distinct Bridge Accounting role is deferred until its exact duties are approved. It must not be silently merged into Mich.

## Sales quotation and contract

- A Sales Executive or authorized Requester prepares a client quotation before
  a new shipment Budget Request.
- The quotation records client, shipment reference, selling amount, validity,
  and commercial terms.
- GM approval is the normal decision path. DCS can see the queue and use an
  emergency override only with a recorded reason.
- Client acceptance is recorded separately and includes the signed/scanned
  quotation. Only an accepted quotation can originate a new shipment Budget
  Request.
- The signed quotation, later Budget Request, payment, Liquidation, Billing, and
  collection records remain linked by shipment and immutable history.

## Budget Request

- For a new shipment, the Requester selects an accepted quotation; the client
  and manually assigned PIMASCOR shipment reference are carried forward.
- Buying and Selling lines are visibly separate.
- Every line records whether it is a pass-through cost or a service charge.
- Repeated operational charge descriptions use a controlled list with a clear custom-entry path.
- The list and detail view show client, shipment reference, requester, dates, Buying, Selling, payment source, payment state, and the next available action.
- Requester actions are Save Draft and Submit for Review. Mich checks the
  initial entry, then the GM approves, rejects, or returns it. Approval and
  payment controls never appear in the request form.
- An Additional Budget links to one original shipment, states the reason, and identifies the related Liquidation expense.
- Additional Budget approval and payment are independent records and never overwrite the original budget.

## Approval

- Mich sees Budget Requests awaiting initial-entry review. GM sees a single
  prioritized queue containing reviewed Budget Requests, Additional Budgets,
  Requests for Payment, Billing, replacements, and Credit Memos.
- Each item clearly identifies its type, requester, amount, age, and evidence.
- GM can approve or reject with an attributable comment.
- DCS has concurrent visibility and may use an exceptional, reasoned approval
  override when Mich or GM is unavailable. The audit trail identifies the
  override rather than presenting it as an ordinary GM approval.
- Approval status and payment status are separate. An approval does not claim money was paid.

## DCS for Payment

- Every GM-approved Budget Request, Additional Budget, OPEX, Marketing, Loan Payment, and Other payment request appears in one DCS/CEO queue.
- GM and Mich may read the queue; DCS and Admin act normally. In the current
  demo, GM may use an exceptional DCS Payment override only with a reasoned,
  attributable explanation.
- DCS may pay, place on hold, return for correction, resume, or annotate.
- Actual funding source comes from an administrator-controlled list. The requester does not select the bank account.
- The permanent payment record includes amount, payment date, method, funding source, recipient, transaction reference, note, actor, and time.
- Recording payment requires a PDF/JPEG/PNG bank, check, or transfer proof.
  Payment proof stays private and is not exposed to the Requester.
- The configured baseline contains Bank of PIMASCOR and Advances to DCS; only an Administrator can add or deactivate a funding source.

## Liquidation

- Liquidation starts after DCS records a shipment payment.
- The Requester records actual expenses and attaches receipts/supporting documents.
- The Requester may save a draft or submit; they cannot close the Liquidation.
- Submitted records are immutable to the Requester unless a future correction workflow explicitly reopens them.
- Mich monitors progress and verifies evidence.
- Mich confirms that the original physical receipts were received and may
  retain a photographed handover record before closure.
- Unspent funds require proof of return. Overspend requires proof of reimbursement and the related Additional Budget where applicable.
- Mich closes only after the required proof is present; closure records actor, time, and note.
- Liquidation status is derived from workflow and variance evidence. Users do not manually select it.
- The detail view compares each approved charge with actual spend and calculated variance, and keeps approved Additional Budgets visible beside it.

## Billing

- Use **Billing** in the interface until Bridge Accounting approves an official Philippine tax-document name and calculation policy.
- Mich can prepare Billing after GM approval; Liquidation completion is not a prerequisite.
- Buying, Selling, pass-through costs, service charges, VAT, and withholding remain separate. VAT and CWT are calculated from Administrator-managed, accountant-approved profiles and snapshotted per line.
- Draft Billing is editable, but Mich/Admin must submit it to GM. Finalization is blocked until GM approval; deliberate finalization then freezes the record.
- A correction to finalized Billing is an attributable Admin void and linked replacement proposal, never a silent overwrite or deletion. Mich/Admin initiates the proposal, GM approves it, and the original remains visible.
- A Credit Memo can reduce a finalized balance only after GM approval; the original Billing amount remains visible.
- The record captures client address, category, shipper/consignee, container, destination, vessel, BL/AWB, exchange rate, measurement, itemized service and pass-through charges, VAT, CWT, and signatures.
- Print Official Document / Save PDF renders a separate professional A4 Statement of Account. It uses the PIMASCOR letterhead, formal account and shipment fields, itemized service and reimbursable sections, totals, terms, and signature lines. The application shell, drawer, controls, activity cards, and action buttons are never part of the printable tree.

## Client Payments

- Mich records payment method, check number/list number when applicable,
  receiving bank, payment date, received amount, and optional note. A check
  number is the external identifier for a check; the user is not forced to
  duplicate it in a separate payment-reference field.
- One received payment may be allocated across several finalized Billing records for the same client.
- Partial allocations preserve the remaining balance.
- Allocations cannot exceed the received payment or a Billing balance.
- The interface shows Unpaid, Partially Collected, and Fully Collected states plus aging.
- Do not display “Mich owns allocation”; the permitted actions already communicate ownership.

## Request for Payment

- A single workspace contains OPEX, Marketing, Loan Payment, and Other tabs/types.
- Mich prepares the request, GM decides, and DCS pays from the consolidated queue.
- The requester never chooses the actual bank/funding source.
- Loan principal is required. Interest and penalties/fees are optional and default to zero; the system never guesses them.
- Exact post-payment bookkeeping validation remains provisional until Bridge Accounting approves the workflow.

## Accounting, documents, and administration

- Accounting begins with neutral downloadable CSV exports and an audit trail. Product-specific import mappings and the chart of accounts remain pending Bridge Accounting sign-off.
- The system is an operational control layer, not the general ledger.
  QuickBooks compatibility must first be reviewed with Bridge Accounting;
  automated transfer is a later integration and must avoid duplicate entry.
- Administration gives Bridge PH an Admin-only Activity Monitor for security, workflow, configuration, document, and transaction events. It defaults to non-Admin staff activity; privileged Admin events remain recorded and are available through an explicit filter.
- Monitoring is limited to necessary business metadata. It never records passwords, OTPs, keys, full bank details, keystrokes, screenshots, webcams, or unrelated personal activity. Production requires a transparent staff notice, proportionality/necessity assessment, privacy impact assessment, restricted reviewers, retention policy, and protected centralized log storage.
- Philippine VAT/CWT defaults are configuration, not universal law encoded into a form. Administrators activate accountant-approved profiles; each Billing line preserves the rates and amounts used at creation.
- Document upload stores actual bytes in private Backblaze B2, validates
  size/type/signature, and records SHA-256. The authenticated no-store viewer uses
  type-specific JPEG/PNG and PDF rendering, visible loading/retry states, and API
  byte-range support. In the current demo correction, Mich, GM, DCS, and Admin
  may use the separately authorized, audited download route; Requesters remain
  view-only for protected payment evidence. Production still requires an
  approved malware scanner and retention policy.
- The protected Document Library indexes signed quotations, DCS payment proof,
  Liquidation receipts, physical-original handover photos, and variance proof.
  Authorized staff can search by filename, document type, client/payee, or
  business reference. Requesters cannot open DCS payment evidence.
- Hosted identity provisioning remains operator-controlled through the production
  account manifest. First-login activation and self-service password recovery are
  implemented; passkey/Pocket ID integration remains future work. Recovery uses a
  generic response, a single-use expiring fragment link, persistent identifier/source
  throttling, five-attempt protection, and session revocation after success.
- Demo accounts and business records are synthetic. The daily 03:00 Asia/Manila reset restores the approved baseline and revokes sessions.

## UX and accessibility acceptance rules

- Meet WCAG 2.2 AA as the target, including keyboard operation, visible focus, meaningful labels, sufficient contrast, and consistent help/navigation.
- Interactive targets are at least 24 by 24 CSS pixels; primary touch controls should normally be about 44 pixels high where layout allows.
- Pages use task-focused headings and plain status labels. Avoid unexplained acronyms in action labels.
- Separate “save,” “submit,” “approve,” “pay,” “finalize,” and “close”; these verbs are not interchangeable.
- Destructive or irreversible actions require a clear consequence, deliberate confirmation, and preserved history.
- Empty states explain why the list is empty and what event will populate it.
- Desktop tables remain scan-friendly; narrow screens expose the same information without horizontal mystery or hover-only controls.

## Implemented in this revision

- Corrected role-aware navigation and direct-route authorization.
- Administrator superuser inheritance across Requester, GM, DCS, and Mich
  capabilities, without impersonation or bypassing workflow-state and audit rules.
- Admin-only operational role switching with working role-specific controls, a persistent
  indicator, and a direct return to the full Admin workspace; the authenticated Admin
  identity and audit attribution remain unchanged.
- Consolidated Request for Payment navigation.
- Controlled DCS funding-source selection.
- Persistent Liquidation draft, submission, variance-proof, and Mich closure workflow.
- Persistent Draft → Pending GM Approval → Approved/Rejected → Finalized/Voided Billing workflow.
- Persistent Client Payment and multi-Billing allocation workflow with aging and balances.
- Check/payment register, pre-numbered check field, and SOA allocations.
- Automatic configured VAT/CWT, detailed Billing/SOA metadata, and linked replacement
  proposals and Credit Memos requiring GM or Administrator approval.
- Administrator funding-source and tax-profile controls.
- Admin-only graphical Activity Monitor with staff-first filters, attributable events, and failed-authentication signals.
- Buying/Selling and pass-through/service-charge classification.
- Connected Shipment Profitability dashboard and print-only professional Billing document output.
- Sales Quotation → GM/DCS decision → client acceptance → linked Budget Request.
- Mich initial-entry review before GM Budget approval, plus attributable DCS
  emergency override.
- Private DCS payment-proof capture and physical-original confirmation at
  Liquidation closure.
- Revised synthetic reset data and forward database migration.

## Explicitly incomplete or awaiting a decision

- Liquidation evidence is connected to private Backblaze B2 object upload and authorized inline viewing. Seeded legacy demonstration rows without object metadata remain visibly labeled as metadata-only.
- Billing output is a dedicated, isolated, professional browser print/PDF document using A4 paged-media rules. It is not a legally approved tax document.
- Accounting account mapping, product-specific import mappings, and the Bridge Accounting role await owner decisions.
- Automated QuickBooks transfer, native App Store/Play Store applications, and
  an on-premises NAS mirror are follow-up deployment projects. The current
  deliverable is a responsive installable PWA with private object storage.
- Client/user administration remains an operator-controlled production workflow;
  password recovery is implemented for activated users. Pending accounts continue
  through first-login activation.
- The current PostgreSQL audit table is suitable for the isolated demo. Production requires centralized tamper-resistant retention, alerting, and a documented review cadence.
- Search suggestions are navigational demonstration data rather than a complete indexed global search.

## Shared error detection and reporting

Demo and production must provide the same plain-language, accessible incident
recovery for every signed-in role. Reports notify `alyssa.d@bridge-ph.com` with
operational context and `jk@delegateops.business` with safe technical and Codex
reproduction context only after the user selects **Report for investigation**.
**Dismiss** closes the message without creating a client report, audit event, or
email. See `INCIDENT-REPORTING.md`.

All action results, status updates, form errors, and workflow warnings use the same
attention principle without creating an incident report: a centered, persistent
dialog obscures the workspace, explains what happened and the exact next step,
blocks background interaction, and returns focus to the triggering control after
dismissal. The application does not use disappearing corner toasts.
