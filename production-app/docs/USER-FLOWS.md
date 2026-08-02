# PIMASCOR user flows

These flows implement `REQUIREMENTS-V2.md`. The arrows describe ownership hand-offs, like a folder moving between accountable desks.

## Shipment Profitability after sign-in

```text
User signs in
  -> dashboard loads permitted Budget Requests for the selected month
  -> user filters shipments by operational status
  -> compares approved Selling with Liquidation actual spending
  -> calculates profit and margin
  -> shows Liquidation, collection, outstanding receivable, and aging status
  -> user switches between animated bars and exact figures
Requester sees owned shipments; management roles see their authorized scope
Admin, GM, and DCS also see monthly OPEX, Marketing, Loan Payment, and Other totals
  -> Open Request for Payment leads to the detailed workflow
```

Admin opens the same Approval queue as GM and can approve or return any pending
financial record using explicit Administrator superuser authority. The action is
recorded as Admin; the application does not impersonate the GM.

## Admin God mode role operation

```text
Admin opens Administration -> Controls
  -> selects Requester, GM, DCS, or Mich
  -> application opens that role's workspace and workflow actions
  -> persistent banner identifies the active role operation
  -> Admin performs permitted workflow work as the application superuser
  -> Admin selects Return to Admin to restore the complete workspace
```

This is operational access rather than a read-only preview. It does not sign in as
another person, reveal another password, or replace the Administrator identity in audit
records.

## Sign-in

```text
User enters username/email and password
  -> API verifies Argon2 hash and account status
  -> Resend sends a personalized six-digit code and secure one-click link
  -> User enters the code or opens the link within five minutes
  -> API creates an opaque server session
  -> User lands on Shipment Profitability
```

The code is single-use. Its secret stays in the URL fragment, which the browser removes
before verification so it is not sent in the initial Caddy/CDN request. The Requester
dashboard is limited to owned shipments. A password change, account disable, or demo
reset revokes affected sessions.

### Release update awareness

```text
User completes sign-in after a new production release
  -> PIMASCOR checks the user's latest acknowledged release
  -> dated What's new dialog explains New, Improved, Updated, or Removed items
  -> user selects Continue to workspace (or closes the dialog)
  -> acknowledgement is recorded and the same dialog stays hidden on later logins
```

The announcement uses plain workflow language, does not expose technical details,
and remains keyboard- and screen-reader-friendly. A user who has not acknowledged
the current release sees it again on the next login if acknowledgement could not
be saved. A temporary save failure never blocks access to the workspace.

### Self-service password recovery

```text
User selects Forgot password? and submits username/email
  -> API applies persistent identifier/source throttles
  -> API returns the same generic confirmation for every identifier
  -> eligible activated account receives a single-use fragment reset link
  -> browser removes the token from the address bar before submitting it
  -> user enters and confirms a password of at least 12 characters
  -> API consumes the token, revokes every existing session, and records an audit event
  -> user returns to sign-in and completes the normal email-code step
```

Reset links expire after 15 minutes, permit five token attempts, and never
auto-sign-in or email a password. Unknown, disabled, pending, malformed,
expired, reused, and exhausted requests receive non-disclosing responses.
Pending first-login accounts use the activation flow instead.

## Shipment funding

```text
Sales Executive / Requester creates a client quotation
  -> enters client, manual PIMASCOR shipment reference, amount, validity, and terms
  -> submits to GM
GM approves or returns; DCS may use a reasoned emergency override
Client acceptance is recorded with the signed/scanned quotation
Requester creates Budget Request draft from the accepted quotation
  -> client and shipment reference carry forward
  -> enters separate Buying and Selling lines
  -> classifies pass-through and service-charge lines
  -> saves draft, reopens it to correct details, or submits to Mich
Mich verifies the initial entry or returns it for correction
GM opens Approval
  -> approves or rejects with an attributable comment
Approved item appears in DCS for Payment
DCS records payment from a configured funding source
  -> attaches bank/check/transfer proof
  -> payment history preserves actor, date, reference, proof metadata, and note
```

Approval says the request is authorized; Record Payment says money actually moved. They never happen through the same button.
Only the owning Requester may edit a Draft or returned request. Submission locks the record; later corrections follow the return or Additional Budget workflow.

## Additional Budget

```text
Requester opens the original shipment
  -> requests Additional Budget
  -> states reason and matching Liquidation expense
  -> submits
GM decides the Additional Budget independently
DCS pays the approved additional amount independently
Original shipment, Additional Budget, and Liquidation retain their links
```

The original record is never edited to hide that more money was requested.

## Liquidation

```text
DCS shipment payment creates Liquidation eligibility
Requester opens My Liquidations
  -> records actual expenses
  -> attaches receipt/supporting-document metadata
  -> saves draft or submits
System calculates released minus actual
Mich opens Liquidations to Review
  -> checks receipts and actuals
  -> confirms receipt of original physical documents
  -> may attach a photographed handover record
  -> records return proof for unspent funds, or reimbursement proof for overspend
  -> records closure note
  -> closes Liquidation
```

The Requester cannot edit after submission or close their own Liquidation. Mich cannot close a non-zero variance without the matching proof.

## Billing

```text
GM approval makes a shipment eligible for Billing
Mich opens Prepare Billing
  -> reviews Selling lines and classification
  -> enters issue/due dates, identity fields, and note
  -> system calculates VAT/CWT from approved profiles
  -> saves editable draft
Mich submits draft to GM
GM approves or returns the Billing proposal
Mich explicitly finalizes an approved proposal
  -> record becomes immutable
  -> authorized users inspect the scrollable A4 preview, zoom from 40% to 160%, and print / save PDF
If correction is required
  -> Admin voids with a reason
  -> original history remains visible
  -> Mich initiates a linked replacement proposal
  -> GM approves it before finalization
Credit Memo
  -> Mich creates a separate adjustment proposal
  -> GM or Administrator approval is required before the balance changes
```

Billing does not wait for Liquidation. “Billing” remains the product term until Bridge Accounting approves formal document terminology.

## Client Payments

```text
Client money reaches PIMASCOR
Mich opens Client Payments
  -> selects client
  -> records external reference, receiving bank, date, and amount
  -> allocates across one or more finalized Billing records
API checks client match and prevents over-allocation
Balances become Unpaid, Partially Collected, or Fully Collected
GM and DCS may review but cannot change allocations
```

## Non-shipment Request for Payment

```text
Mich opens Request for Payment
  -> chooses OPEX, Marketing, Loan Payment, or Other
  -> enters payee, purpose, amount/breakdown, and support
  -> saves draft or submits
GM decides in Approval
Approved item appears in DCS for Payment
DCS chooses the configured funding source and records payment
```

The actual bank is DCS's controlled choice, not part of Mich's request. Loan interest and fees default to zero and are never guessed.

## DCS exception handling

```text
DCS opens approved payable
  -> Pay: records actual movement of money
  -> Hold: pauses with reason
  -> Return: sends back for correction with reason
  -> Resume: returns held item to pending
  -> Annotate: adds context without changing state
```

Every annotation is chronological. Returning or holding never erases GM approval.

## Bridge PH supervision

```text
Admin opens Administration -> Activity Monitor
  -> defaults to non-Admin staff activity
  -> filters 7/30/90 days, event type, staff, or reference
  -> reviews security signals, money movements, workflow/configuration changes,
     active actors, and the attributable timeline
  -> optionally includes Admin events for privileged-action review
```

The monitor observes actions inside PIMASCOR, not the employee's device. Every monitor view is recorded. Passwords, email codes, keys, full bank details, keystrokes, screenshots, webcams, and unrelated personal activity are outside its scope.

## Demo reset

```text
03:00 Asia/Manila -> API briefly stops accepting changes
                    demo document objects are deleted,
                    one database transaction deletes mutable demo records,
                    inserts the approved synthetic baseline, and revokes sessions
                    API restarts after the transaction commits
Users sign in again -> familiar training scenario is restored
```

No S3 object or database backup is read. The reset is like clearing and restocking a training showroom from a master checklist kept in the application code, including shredding the temporary documents left by the previous class.

## Any signed-in role: recover from an app problem

```text
Error detected -> plain explanation + safe next step
               -> Dismiss: close locally; no client report or email
               -> Report for investigation: create/confirm private reference
                  + separate Admin/Developer emails
               -> close after both deliveries are confirmed
```

If transaction completion is uncertain, the guidance instructs the user to check
the relevant list before retrying. No form contents or confidential values enter
the incident report.

Routine action results, status updates, form validation, and workflow warnings use
the centered feedback dialog instead of a corner toast. They block background
interaction and remain until deliberately dismissed, but do not create an incident,
audit event, or email.
