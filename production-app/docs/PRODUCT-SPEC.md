# PIMASCOR product specification

Version: evaluation revision v2  
Controlling requirements: `REQUIREMENTS-V2.md`

## Purpose

PIMASCOR is an internal operational and financial control system for PIMASCOR/Bridge PH. It replaces loosely connected forms and sheets with a visible chain from request through approval, payment, Liquidation, Billing, and client collection. It is not a public website and the demo is not authorized for live data.

## Product principles

- Show each role only the work it needs.
- Use task language, not implementation language.
- Keep approval, payment, Liquidation, Billing, and collection as distinct events.
- Preserve actor, time, reason, version, and evidence for material actions.
- Never silently overwrite finalized financial records.
- Never guess tax, interest, penalties, bank account, or accounting treatment.

## Navigation by role

| Workspace | Admin | Requester | GM | DCS | Mich |
|---|---:|---:|---:|---:|---:|
| Shipment Profitability | All | Own | All | All | All |
| Sales Quotations | All | Own/create | Approve | Read/override | Read |
| Budget Requests | All | Own/create | Read | Read | Read |
| Approval | Decide | No | Decide | Emergency override | Initial review |
| DCS for Payment | Act | No | Read | Act | Read |
| Liquidations | All | Own/create | Read | Read | Review/close |
| Billing | Prepare/submit/finalize approved | Own final | Approve | Read | Prepare/submit/finalize approved |
| Client Payments | All | No | Read | Read | Record/allocate |
| Request for Payment | All | No | Read | Read | Create |
| Accounting | Yes | No | No | No | No |
| Administration | Yes | No | No | No | No |

Direct URLs receive the same authorization check as navigation. A hidden menu item is not a security boundary.

Admin is the explicit application superuser. It can perform every Requester, GM,
DCS, and Mich capability plus Administration and Accounting actions. Admin never
impersonates another role: the original Admin identity is stored in the audit trail,
and all normal state, version, evidence, confirmation, CSRF, and validation rules
still apply.

Administration includes an Admin-only operational role switch. Selecting Requester,
GM, DCS, or Mich opens that role's navigation and real workflow controls without changing
the authenticated account. A persistent banner identifies the active role workspace and
returns the operator to Admin. Actions are authorized through Admin's superuser access
and remain attributable to the signed-in Administrator.

## Bridge PH Activity Monitor

Administration opens on an Admin-only supervision view with daily activity, review signals, money movements, active staff, category distribution, actor summaries, and recent attributable events. Filters cover 7/30/90 days, type, staff/reference search, and optional Admin activity.

The default is **staff activity**. Admin activity is still recorded and can be included because privileged users must not become an audit blind spot. The monitor records business-system events only. It does not capture passwords, email codes, keys, full bank details, keystrokes, screenshots, webcams, or unrelated personal activity.

Before production, Bridge PH must publish the monitoring purpose/scope, complete a privacy impact assessment, define reviewers and retention, and connect serious signals to protected centralized logging/alerting.

## Shared interaction model

Every work queue provides a plain-language title, short explanation, type/status, responsible party, important amount/date, and a clear Open action. Empty states explain the event needed to create work. Forms separate reversible actions from state-changing actions:

- **Save Draft** keeps work editable.
- **Submit for Approval** hands ownership to GM.
- **Approve/Reject** records GM's decision.
- **Record Payment** confirms money moved.
- **Finalize Billing** freezes the client charge record.
- **Close Liquidation** confirms evidence and variance resolution.

Buttons use those verbs consistently; “process” and “execute” are avoided where a clearer verb exists.

## Budget Requests

The form contains:

- Accepted quotation selection for a new shipment.
- Client and manual PIMASCOR shipment reference carried from that contract.
- Request date and currency.
- Separate Buying and Selling sections.
- Each line's description, pass-through/service-charge classification, and amount.
- Controlled common charge descriptions plus custom entry.

The Requester can save or submit for Mich review. Mich verifies the initial
entry, then GM decides. DCS may use a reasoned emergency override when the
normal reviewers are unavailable. GM and payment controls are absent from the
request form. Monthly filtering uses the request date and displays totals
without mixing Buying and Selling.

## Sales Quotations

A Sales Executive or authorized Requester creates a quotation with client,
shipment reference, selling amount, validity, and terms. GM approval is normal;
DCS has read access and a reasoned emergency override. Client acceptance and the
signed PDF/JPEG/PNG contract are recorded separately. A new shipment Budget
Request cannot be linked until the quotation is accepted.

### Additional Budget

An Additional Budget begins from an existing original shipment and records:

- Parent request and shipment.
- Operational reason.
- Related Liquidation expense description and amount.
- Additional Buying lines.

It follows its own submit, GM decision, and DCS payment states. The parent remains unchanged and links both directions.

## Approval

GM receives a single queue for submitted Budget Requests, Additional Budgets, and Requests for Payment. The detail view shows evidence and context before Approve or Reject. A decision records actor, timestamp, reason/comment, and record version.

## DCS for Payment

All GM-approved payable types enter one DCS/CEO queue. Each item shows type, reference, party/client, approved total, paid total, outstanding amount, requester, and notes.

DCS/Admin actions:

- Record full or allowed staged payment.
- Place on hold with reason.
- Return for correction with reason.
- Resume a held item.
- Add a chronological annotation.

Payment records include date, method, administrator-configured funding source,
recipient, external transaction reference, note, actor, time, and verified
PDF/JPEG/PNG proof. The original GM decision remains visible after a hold or
return. Requesters cannot enter the payment workspace or open its confidential
proof.

The protected Document Library indexes signed quotations, payment proof,
Liquidation receipts, physical-original handover photos, and variance evidence.
Authorized staff can search by filename, type, client/payee, or reference. It
offers view-only no-store rendering and no download action.

## Liquidations

After a shipment payment, the original Requester can create a Liquidation draft. They enter actual expense lines and receipt/supporting-document metadata. Submission requires at least one receipt when actual spend is positive.

The system compares total released funds from the original and paid Additional Budgets against actual spend:

- Zero variance: Mich may verify and close.
- Money remaining: proof of returned funds is required.
- Overspend: proof of reimbursement is required, and an Additional Budget should link the corresponding expense where applicable.

Requester editing stops after submission. Mich confirms receipt of the physical
originals, may upload a handover photo, records evidence and closure note; the
API records actor/time and makes the closed record immutable.

## Billing

Billing may begin after GM approval and does not wait for Liquidation. Mich/Admin selects an eligible Budget Request and prepares an editable draft containing issue/due dates, client and shipment identity fields, separately classified lines, automatically calculated VAT/CWT, and notes. Active tax profiles are Administrator-managed; the applied rates and calculated amounts are snapshotted on each line.

The interface calls it **Billing**, not Invoice, until Bridge Accounting approves formal tax terminology. It visibly states that the preview is not automatically an official tax invoice.

Mich/Admin submits a draft for approval. GM or Admin can approve or return it, and finalization is blocked until Approved status. Explicit finalization freezes content. Only Admin can void finalized Billing, with a required reason and preserved original. Mich/Admin may initiate a linked replacement proposal with a temporary proposal reference. Its official `-R#` reference is assigned only after GM or Admin approval, and it cannot finalize while the original remains finalized. Credit Memos require GM or Admin approval and adjust the collectible balance without rewriting the original. Print Official Document / Save PDF uses a separate A4 Statement of Account tree modeled on PIMASCOR's formal document. Application navigation, drawers, buttons, and status cards cannot spill into the printout.

## Client Payments

Mich/Admin records money received from a client with payment method, check
number/list number when applicable, bank/transfer reference when applicable,
receiving bank, date, total amount, and note. A check number is reused as the
external reference rather than entered twice. The amount can be allocated
across multiple finalized Billing records for the same client.

Rules:

- Total allocation cannot exceed the received amount.
- Allocation cannot exceed a Billing balance.
- All selected Billing records belong to the selected client.
- The same Billing record appears once per payment.
- Unallocated funds remain visible rather than disappearing.

The queue shows Unpaid, Partially Collected, or Fully Collected, remaining balance, due date, and aging days. GM/DCS are read-only.

## Request for Payment

One workspace contains OPEX, Marketing, Loan Payment, and Other types. Mich creates, GM approves/rejects, and DCS pays. The request captures payee/party, purpose, request date, due date where relevant, amount or loan breakdown, notes, and supporting metadata. It does not ask Mich to choose the actual funding bank.

For Loan Payment, principal is required; interest and penalties/fees are optional zeros. The displayed total is calculated and validated by the API. A future Bridge Accounting decision will determine any additional post-payment validation step.

## Shipment Profitability and reports

Every role lands on Shipment Profitability. Requesters see only their own shipments; management roles see all permitted shipments. Selling comes from approved Budget Requests, actual spending from Liquidations, and collection/aging from finalized Billing and allocations. Profit equals selling less actual spending; margin equals profit divided by selling. The accessible bar comparison is paired with a complete data table.

## Search and notifications

Current global search is a navigational demonstration. Production requires indexed, permission-filtered results from reference, shipment, client, Billing, and payment records. Notifications must become persistent and attributable before “mark all read” is considered complete.

Every action result, status update, form validation error, and workflow warning opens
a centered modal dialog with a dimmed/blurred background, a plain explanation, an
exact next step, and a deliberate dismissal button. Messages never disappear in a
corner toast. Routine feedback does not create an incident, audit event, or email.
Detected application, browser, or server failures retain the separate centered
incident dialog with **Dismiss** and **Report for investigation**.

## Authentication and sessions

- Username/email plus Argon2-protected password.
- Personalized Resend email verification with a six-digit, single-use, five-minute
  code, accessible plain text, modern image-free HTML, and a secure one-click link.
- Opaque server-side session cookie with Secure, HttpOnly, and SameSite controls.
- Separate non-HttpOnly CSRF cookie and header for mutations.
- Session expiry and revocation after password changes, account disable, and demo reset.
- No role simulator in the authenticated UI.

Pocket ID or another external identity provider is a later revision after the current access matrix stabilizes.

## Documents and retention

Document handling uploads bytes to private Backblaze B2, verifies supported file
signatures and size, stores integrity metadata, authorizes every index/view, and logs
views. The authenticated no-store viewer renders JPEG/PNG files as images and PDFs
in a dedicated PDF frame; it shows loading, retry, and reportable failure states
instead of an empty panel. The API supplies correct MIME, length, inline, and byte
range headers. The application exposes no document download control and the old
download endpoint returns `403`. Production must add the approved malware scanner
and retention policy. Podman secrets supply credentials; no `.env` files or usable
keys belong in source or Quadlets.

## Demo behavior

The demo contains realistic but fictional data. Users may create and modify make-believe transactions. At 03:00 Asia/Manila, the reset job locally replaces mutable business/configuration records with the code-defined baseline and revokes sessions while preserving user accounts/password hashes. The demo has no backup or S3 restore dependency.

## Production blockers

- Bridge Accounting role and posting/tax rules.
- Approved malware scanning and document-retention enforcement.
- Archival PDF requirements.
- Complete identity/user lifecycle and password recovery.
- Persistent notification and global search services.
- Centralized tamper-resistant audit retention/alerting, rate limits, restore rehearsal, accessibility/privacy review, and owner acceptance.

## Incident recovery

Every signed-in role receives plain-language error context, a suggested next step,
and two unambiguous choices: dismiss without reporting, or report for investigation.
Admin and Developer notifications are separate, consent-based, and exclude form
values and confidential data. See `INCIDENT-REPORTING.md`.
