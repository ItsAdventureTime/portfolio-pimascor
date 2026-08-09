# PIMASCOR revised demo acceptance checklist

Use separate real demo accounts for every role. Check an item only after the named owner performs it in the hosted demo. Use fictional data.

## Language and navigation

- [ ] Employees find shipment funding under Budget Requests without explanation.
- [ ] GM finds all decisions under Approval.
- [ ] DCS understands DCS for Payment as the list requiring CEO action.
- [ ] OPEX, Marketing, Loan Payment, and Other are easy to find inside Request for Payment.
- [ ] The interface consistently spells Mich.
- [ ] The interface uses Billing and explains that it is not automatically an official tax invoice.

## Permissions

- [ ] Requester lands on Shipment Profitability and sees only owned shipment data.
- [ ] Requester cannot access funding sources, approvals, DCS actions, accounting, or administration by menu or direct URL.
- [ ] GM exclusively decides submitted Budget, OPEX, Marketing, Billing, replacement Billing, and Credit Memo work.
- [ ] DCS can mutate only DCS for Payment and selects a configured funding source.
- [ ] Mich can prepare Request for Payment/Billing/Client Payment and close Liquidations, but cannot approve or make DCS payments.
- [ ] Admin can perform controlled void and operational administration.

## Budget Request and approval

- [ ] Client and manual shipment reference are clear.
- [ ] Buying and Selling are visibly separate.
- [ ] Pass-through cost and service charge are explicit per line.
- [ ] Requester has only Save Draft and Submit for Approval.
- [ ] GM decision records comment, actor, and time.
- [ ] Additional Budget links original shipment, reason, and corresponding Liquidation expense without overwriting the original.

## DCS for Payment

- [ ] Every GM-approved shipment, additional budget, OPEX, Marketing, and Loan Payment reaches one queue.
- [ ] Approval and payment status are visibly separate.
- [ ] DCS can pay, hold, return, resume, and annotate.
- [ ] Free-typed/unconfigured funding source is rejected by the API.
- [ ] GM/Mich can inspect but cannot mutate the queue.

## Liquidation

- [ ] Requester can save actual expenses and upload private receipt files only after payment.
- [ ] Submission without required receipt is rejected.
- [ ] Requester cannot edit after submission or close the record.
- [ ] Unspent funds require return proof; overspend requires reimbursement proof.
- [ ] Mich closure records note, actor, time, and freezes the record.

## Billing

- [ ] Billing becomes available after GM approval without waiting for Liquidation.
- [ ] Mich can edit a draft.
- [ ] Mich submits Billing for approval; GM or Admin can approve it.
- [ ] Replacement Billing begins as a pending proposal and cannot bypass GM/Admin approval.
- [ ] Credit Memos require GM or Admin approval.
- [ ] Only approved Billing can be deliberately finalized; finalization prevents later edit.
- [ ] Admin void requires a reason and does not delete history.
- [ ] Print Official Document / Save PDF prints only the professional A4 document.

## Client Payments

- [ ] Mich records reference, receiving bank, payment date, and amount.
- [ ] One payment can be allocated across multiple Billing records for the same client.
- [ ] Partial payment keeps the correct balance and status.
- [ ] Over-allocation and cross-client allocation are rejected.
- [ ] Aging is understandable and GM/DCS remain read-only.

## Shipment Profitability

- [ ] Every role lands on the connected dashboard.
- [ ] Selling and actual spending match the Budget Request and Liquidation.
- [ ] Profit, margin, Liquidation, collection, outstanding amount, and aging are correct per shipment.
- [ ] The bar comparison has an equivalent exact-value table and remains readable on mobile.

## Confidential documents

- [ ] Authorized users can view a private document through the inline viewer.
- [ ] No document download control appears and `/documents/{id}/download` is denied.

## Usability and accessibility

- [ ] Full workflow is keyboard-operable with visible focus.
- [ ] Controls have meaningful labels and no hover-only operation.
- [ ] Touch users can operate primary controls comfortably.
- [ ] Status is conveyed by text, not color alone.
- [ ] A recoverable app problem explains what happened and what to do next without technical language.
- [ ] Dismiss closes without a client report, audit event, or email.
- [ ] Report for investigation sends both private emails and closes after delivery.
- [ ] The incident dialog works at desktop and mobile widths and has no horizontal scrollbar.
- [ ] Every action result, status update, form error, and warning opens a centered
  persistent dialog rather than a corner toast; the dialog names what happened and
  the exact next step.
- [ ] Validation dialogs remain until dismissed, block background interaction, keep keyboard focus inside, support Escape, and return focus to the triggering control.
- [ ] Successful confirmations require a deliberate **Close and continue** action and
  restore focus to the control that triggered them.
- [ ] Firefox and Chromium-family browsers load scripts/styles under the deployed CSP.
- [ ] Desktop and narrow layouts retain all key information.
- [ ] Empty and error states explain the next useful action.

## Operations

- [ ] API and database publish no host ports; Caddy remains the only public entry.
- [ ] Podman secret values do not appear in source, Quadlets, logs, or command history.
- [ ] No demo backup/dump/retention timer is installed; production backup definitions remain separate.
- [ ] 03:00 Asia/Manila reset removes demo document objects, restores realistic synthetic data, preserves accounts/password hashes, and revokes sessions without reading a backup.
- [ ] Generated reset service uses `APP_ENV=maintenance`, receives database and Backblaze credentials through Podman secrets, and does not require API-only email or session secrets.
- [ ] API service reports healthy through the Quadlet runtime health check; the API image contains no redundant Docker-format `HEALTHCHECK`.
- [ ] PostgreSQL uses the exact `data/postgres/18/docker` bind mount and restarts without a rootless permission error.
- [ ] Forward migration succeeds on a copied database before the live update.
- [ ] Migration `20260723_0008` is current and incident reports appear under Administration → Activity Monitor → App problems.
- [ ] Admin and Developer receive separate incident emails through the Resend Podman secret; neither email includes secrets, full bank details, document contents, or form entries.
- [ ] Admin email uses plain operational/accounting language; Developer email contains a reproducible technical summary and a ready-to-copy Codex investigation prompt.
- [ ] Local rollback web files and previous API image remain until acceptance.

## Decisions required before production

- [ ] Bridge Accounting role and ownership.
- [ ] VAT/CWT/EWT, chart of accounts, journal, official tax-document terminology, and void/replacement rules.
- [ ] Malware scanning and approved document retention.
- [ ] Archival PDF requirements.
- [ ] Password recovery, account lifecycle, notification, and global-search scope.
- [ ] Management-approved RPO, RTO, retention, and restore-test cadence. The
  current release uses fixed four-times-daily base backups plus encrypted
  Restic retention; Admin/DCS catalog access is read-only and restoration is
  owner-only CLI with dry-run and quarantine evidence.

## Sign-off

| Owner | Scope | Name/date | Accepted changes or blocker |
|---|---|---|---|
| Requester representative | Budget Request and Liquidation entry |  |  |
| GM | Approval and read views |  |  |
| DCS / CEO | DCS for Payment |  |  |
| Mich | Request for Payment, Billing, Client Payments, Liquidation review |  |  |
| Admin / IT | Identity, audit, deployment, backup/restore |  |  |
| Bridge Accounting | Deferred accounting/tax decisions |  |  |

Admin / IT acceptance also confirms the staff notice/PIA owner, authorized monitor reviewers, audit retention/review cadence, escalation contacts, and production centralized/tamper-resistant logging destination.
