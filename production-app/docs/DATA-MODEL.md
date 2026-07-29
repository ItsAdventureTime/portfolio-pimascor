# PIMASCOR data model

This is the current conceptual model. PostgreSQL migrations are the executable schema; `REQUIREMENTS-V2.md` controls business meaning.

## Identity and control

### users

Username, unique email, display name, Argon2 password hash, role, account status, verification and timestamps. Historical users are disabled rather than deleted.

### auth_challenges and sessions

Short-lived hashed email-code challenges and opaque server sessions. Session values are never stored in clear text. Password change, account disable, and demo reset revoke sessions.

### audit_events

Actor, action, entity type/id, privacy-minimized reason, correlation identifier, and occurrence time. Admin monitoring derives category/severity labels and summaries without copying secrets or email addresses. Audit history is append-only at the application boundary; production still requires protected centralized retention and alerting.

## Reference data

### clients

Stable code, name, and active state.

### funding_sources

Administrator-controlled display name and active state. Only these values may be selected when DCS records payment. Deactivation does not alter historical payment snapshots; duplicate names are rejected case-insensitively.

### tax_profiles

Administrator-controlled name, service/pass-through classification, VAT rate, withholding rate, and active state. One active profile per classification makes calculation deterministic; historical Billing lines retain their snapshots.

## Shipment funding

### sales_quotations

Sequential reference, client, manual shipment reference, selling amount,
currency, validity, terms, Draft/Pending Approval/Approved/Returned/Accepted
status, version, preparer, normal or override decision, client-acceptance time,
and signed-document filename/object key/content type/size/SHA-256.

### budget_requests

Reference, original/additional kind, parent, optional originating accepted
quotation, client, manual shipment reference, request date, currency, Mich
review actor/time/note, status, approval fields, separate payment status,
version, and requester.

### budget_items

Buying/Selling kind, pass-through/service-charge classification, description, amount, and order.

### releases and payment_annotations

Actual payment amount/date/method/source/recipient/external reference/note/actor,
private proof filename/object key/content type/size/SHA-256, plus chronological
payment-state annotations. Approval remains on the request and is never inferred
from a release.

## Request for Payment

### expense_requests

OPEX/Marketing/Loan Payment/Other type, party, purpose, dates, amount, optional loan breakdown, notes, lifecycle/approval/payment status, requester, version, and timestamps. The former requested funding source is nullable because DCS owns the actual source choice.

### expense_validations

Legacy/provisional post-payment Loan Payment validation. Retained for compatibility; its future meaning requires Bridge Accounting approval.

## Liquidation

### liquidations

One per original Budget Request. Stores requester, released total, actual total,
Draft/Submitted/Pending Variance/Closed status, physical-originals confirmation
and time, version, submit/close actor and time, and closure note.

### liquidation_lines

Actual expense description, amount, and order.

### liquidation_evidence

Receipt, return proof, or reimbursement proof; original filename, private object key, content type, byte size, SHA-256, uploader, and time. New uploads bind to a real private Backblaze object. Authorized users receive inline, no-store views; the application disables downloads. Legacy seeded rows without integrity metadata are labeled metadata-only.

## Billing and collection

### billing

Reference, original Budget Request, optional replacement link/revision, issue/due dates, client address, category, shipper/consignee, container, destination, vessel, BL/AWB, exchange rate, measurement, service and pass-through subtotals, VAT, withholding, total, net due, Draft/Pending Approval/Approved/Rejected/Finalized/Void status, version, notes, preparer/submitter/GM approver/finalizer/void actor and times, rejection reason, and void reason.

### billing_lines

Description, pass-through/service-charge classification, amount, applied VAT/CWT rate and amount snapshots, and order.

### credit_memos

Reference, finalized Billing link, reason, amount, Pending Approval/Approved/Rejected status, version, creator, GM approver, decision time, and rejection reason. Approved values reduce the collectible balance without changing the original Billing amount.

### client_payments

Internal reference, client, payment method, check number and pre-numbered check-list reference where applicable, external payment reference, receiving bank, payment date, received amount, note, recorder, and time.

### payment_allocations

Join from one Client Payment to one finalized Billing record with allocated amount. Several allocations may belong to one received payment.

## Important constraints

- Email, username, major record references, and derived/external
  client-payment reference are unique.
- An originating quotation must be accepted and match the Budget Request client
  and shipment reference.
- Money uses fixed decimals; never binary floating point in storage.
- Buying and Selling totals are never merged into one ambiguous amount.
- Additional Budget parent is an original shipment; the original row is not overwritten.
- Requester can access only owned Budget Requests, Liquidations, and finalized Billing.
- A Liquidation draft is editable; submitted/closed states are protected.
- Non-zero Liquidation variance needs the matching proof before closure.
- Billing is editable in Draft or after rejection. Submission locks content; GM or
  Administrator decides; only Approved Billing can be finalized.
- A replacement is a linked proposal pending GM approval and never overwrites its original. Its official `-R#` reference is assigned only when the GM approves it.
- Client Payment allocation does not exceed payment total or Billing balance and must match the Billing client.
- Material mutations use optimistic version checks.
- Demo reset deletes business records in dependency order, recreates a coherent fictional baseline, preserves users/password hashes, and revokes sessions.

## Environment isolation

Demo and production use separate PostgreSQL containers, directories, databases, secrets, cookies, networks, and Backblaze prefixes. A production database is never restored over the demo or vice versa without an explicit isolated recovery procedure.

## IncidentReport

`IncidentReport` stores a unique reference, optional actor, source, severity, safe
operation/page/request metadata, plain user message, recovery suggestion, correlation
ID, deployment tier, and email-delivery timestamps. Client/browser errors are stored
only after the user selects **Report for investigation**. Server failures may retain
a protected diagnostic reference without sending email. It never stores form
payloads, documents, credentials, session values, secret keys, or full bank
information. A client UUID makes creation idempotent.
