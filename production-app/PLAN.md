# PIMASCOR revised delivery plan

Updated: 23 July 2026  
Current target: team demo at `https://delegateops.business/pimascor/demo/`

## 1. Source of truth

Implementation follows `docs/MEETING-DECISIONS-2026-07-24.md` and
`docs/REQUIREMENTS-V2.md`. Historical prompts, screenshots, and generated
handoff snapshots are archived outside the active documentation surface. The
correct name is **Mich**.

Operational and deployment assertions follow `docs/FACTUAL-BASIS.md`; an
unverified server, storage, CDN, or migration state is recorded as unknown.

## 2. Product outcome

PIMASCOR provides one accountable path from operational request to approval, payment, Liquidation, Billing, and collection. The demo uses realistic fictional records, resets at 03:00 Asia/Manila, and must never hold live financial or personal data.

## 3. Confirmed technology

- React, TypeScript, and Vite static PWA served by Caddy.
- FastAPI on the controlled current Python branch.
- PostgreSQL 18 in a separate rootless Quadlet with versioned `PGDATA`.
- Username/password plus Resend email code, server sessions, CSRF, and Argon2.
- Private Backblaze B2 through its S3-compatible API.
- Rootless Podman Quadlets on Fedora CoreOS; only Caddy publishes host ports.

Think of React as the reception forms, FastAPI as trained staff checking each request, PostgreSQL as the records room, and Caddy as the only public entrance.

## 4. Information architecture

1. Shipment Profitability, shown after sign-in to every role; Requesters see
   only owned shipments. Bridge Accounting uses the Admin capability set.
2. Budget Requests / My Budget Requests.
3. Approval.
4. DCS for Payment.
5. My Liquidations / Liquidations to Review.
6. Billing / Prepare Billing.
7. Client Payments.
8. Request for Payment: OPEX, Marketing, Loan Payment, and Other.
9. Accounting, Admin only pending the accounting role.
10. Clients & Documents.
11. Administration: Bridge PH Activity Monitor plus approved funding/tax controls.

## 5. Ownership

- Requester: own Budget/Additional Budget requests, Liquidation expenses and receipts, and finalized Billing.
- GM: approve/reject; read payments, Billing, Client Payments, and expenses.
- DCS / CEO: pay, hold, return, resume, and annotate in DCS for Payment.
- Mich: create Requests for Payment; prepare Billing; record Client Payments; verify and close Liquidations.
- Admin / Bridge PH: full access, controlled funding sources, attributable void authority, and privacy-minimized supervision.
- Bridge Accounting: deferred until duties are approved.

## 6. Workflow

```text
Budget Request -> GM decision -> DCS payment -> Requester Liquidation -> Mich close
                       |
                       +-> Mich Billing -> Client Payment allocation

Request for Payment -> GM decision -> DCS payment
```

Additional Budgets remain linked to the original shipment and corresponding Liquidation expense. Approval and payment are separate states.

## 7. Delivered

- Role-correct navigation and API authorization.
- Connected Budget, Additional Budget, Approval, DCS payment, Liquidation, Billing, Client Payment, and Request for Payment workflows.
- Controlled Admin-only funding-source/tax-profile maintenance.
- Admin-only Activity Monitor with staff-first filters, daily graphics, security/transaction/workflow categories, actor summaries, and attributable events.
- Failed password/email-code signals without submitted secrets. Admin actions remain recorded and can be included explicitly.
- Private B2 document upload, responsive type-specific view-only previews with
  loading/retry states and byte-range support, 100 MB validation, and integrity
  metadata. Production authorized staff can use audited downloads; demo is
  inline-only and has no download route.
- 03:00 code-defined demo reset with no backup restore.
- Rootless Quadlets, guarded updater, local rollback material, and PostgreSQL ownership/health fixes.
- Centered persistent action feedback with no corner toasts, animated dashboard
  values and bars, short interface motion, touch layouts, and `prefers-reduced-motion`.

## 8. Verification

- Historical July evidence reported 45 API tests. Current release evidence is
  maintained in `docs/QUALITY-ASSURANCE.md`; do not reuse historical counts.
- TypeScript compilation and optimized Vite build passing.
- Desktop 1280px and mobile 390px browser checks: no horizontal overflow or console warnings.
- Role walkthrough remains required on the hosted demo.

## 9. Production blockers

1. Bridge Accounting decisions for tax terminology, chart of accounts, journals, and document rules.
2. Approved malware scanning, document retention, and archival PDF requirements.
3. User/client administration, password recovery, persistent notifications, and indexed search.
4. Centralized tamper-resistant audit retention/alerting, rate limits, image/dependency scanning, and incident runbook.
5. Employee-monitoring notice, privacy impact assessment, authorized reviewers, and retention/review cadence.
6. Restore rehearsal, accessibility/privacy review, and owner acceptance.

## 10. Promotion rule

Production receives separate Quadlets, networks, secrets, cookies, database, Backblaze prefixes, retention policy, accounts, and acceptance evidence under:

```text
~/bridge-ph/pimascor
~/.config/containers/systemd/bridge-ph/pimascor
```

The demo does not become production by renaming a directory.

## 11. Shared incident recovery

Demo and production use the same incident model, accessible recovery UI, audit
events, and separate Admin/Developer emails. Production changes only isolated
credentials and deployment settings. The controlling contract is
`docs/INCIDENT-REPORTING.md`.
