# PIMASCOR API

FastAPI application for PIMASCOR's authenticated operational and financial workflows.

## Local development

The default local database is SQLite so the application can run without installing a database server. PostgreSQL remains the production database and can be selected with `DATABASE_URL`.

```bash
cd apps/api
uv sync --extra dev
uv run python -m pimascor_api.seed
uv run uvicorn pimascor_api.main:app --reload --port 8000
```

Local development uses the safe defaults in the application. If a non-default,
non-secret value is needed for a single command, provide it in that command's
shell environment; do not create an `.env` file. Hosted configuration belongs
in the Quadlet `.container` file, while usable credentials remain mounted Podman
secret files.

The seed command prompts for the account password instead of placing a password in source code or shell history. Use `--role` to create Requester, GM, DCS, or Mich demo accounts. API documentation is available at `http://127.0.0.1:8000/docs`.

For the hosted demo, routine account operations remain CLI-only so the illustrative Admin screen cannot be mistaken for a completed identity-management system:

```bash
python -m pimascor_api.account_admin list
python -m pimascor_api.account_admin set-password requester
python -m pimascor_api.account_admin disable requester
python -m pimascor_api.account_admin enable requester
```

Password changes and account disabling revoke active sessions. Disable accounts instead of deleting them so historical audit actions retain their actor.

Production role bootstrap uses `python -m pimascor_api.bootstrap_accounts` with
the Section 1 account manifest mounted from a rootless Podman secret. It
creates pending accounts without passwords. The user receives an email OTP,
then chooses a 12-character minimum password through
`/auth/activation/complete`; permanent passwords are never sent by email.

In development, email verification codes are written to the API log and returned in
the password-start response. Production mode refuses this delivery mechanism. Resend
sends a personalized HTML and plain-text message with a large six-digit code and
one-click sign-in link. The code works once for five minutes. Configure the trusted
`PUBLIC_APP_URL` explicitly; hosted mode requires HTTPS. Azure Communication Services
remains an adapter boundary for a later implementation.

## Database

- Local default: `sqlite:///./var/pimascor.db`
- PostgreSQL example: `postgresql+psycopg://pimascor:password@localhost/pimascor`
- Apply migrations: `alembic upgrade head`
- Create a migration: `alembic revision --autogenerate -m "description"`

SQLite is a convenience for one-developer local operation and tests, not the recommended shared production database.

## Connected operational workflows

OPEX, Marketing, Loan Payment, and Other are clear types inside the user-facing **Request for Payment** workspace. They use one protected API engine and remain separately reportable. The basic sequence is:

```text
Mich draft -> GM Approval -> DCS for Payment -> paid
```

The API calculates a Loan Payment total from principal, optional interest, and optional penalties/fees. It rejects a supplied total that does not match that visible breakdown. Any additional accounting-validation step remains provisional until Bridge Accounting approves it.

Shipment workflows now include persistent Liquidation, Billing, and Client Payment records:

- A Sales Executive or authorized Requester creates a quotation; GM normally
  approves it, DCS has a reasoned emergency override, and signed client
  acceptance makes it eligible for a linked Budget Request.
- A Requester submits a Budget Request to Mich for initial-entry review before
  GM approval. A reasoned DCS override remains visibly exceptional and audited.
- DCS/Admin records payment from a configured source and attaches verified
  private payment proof.
- A Requester saves and submits actual Liquidation expenses and receipt
  metadata; Mich confirms receipt of the physical originals, supplies variance
  proof, and closes the record.
- Mich or Admin edits Billing while it is a draft, submits it to the GM, and can finalize it only after GM approval. Finalization freezes it; only Admin can create an attributable void record.
- A replacement starts as a linked proposal submitted by Mich/Admin. GM or
  Administrator approval is required before it can become final, and the original
  is never overwritten. Credit Memos require the same approval.
- Mich or Admin records a Client Payment and may allocate it across several
  finalized Billing records for the same client. A check number is reused as
  its external reference rather than entered twice. The API prevents
  over-allocation and preserves partial balances.
- DCS and Admin choose the actual payment source only from the active administrator-controlled funding-source table.

Liquidation receipts and variance proofs are transferred to private Backblaze B2 through its S3-compatible API. The API verifies PDF/JPEG/PNG signatures in bounded chunks, enforces a 100 MB per-file limit, records SHA-256 and byte size, uses managed multipart transfer, opaque object keys, an authorized document index, and an audited same-origin inline, no-store stream. The download route is denied. Large request bodies spool to a private host directory instead of remaining in API memory. Malware scanning and a management-approved retention policy remain production gates.

`GET /dashboard/shipment-profitability` calculates selling, actual spending, profit, margin, Liquidation status, collection status, outstanding receivables, and aging from persistent records. Requesters receive only their own shipments.

## Demo reset

`python -m pimascor_api.demo_reset` replaces business records with approved fictional scenarios while preserving user accounts. It revokes existing sessions, so users sign in again after a reset. The command refuses to run unless `DEPLOYMENT_TIER=demo`, and requires active Requester, GM, DCS, and Mich accounts.

On the hosted demo, the reset Quadlet runs this command with
`APP_ENV=maintenance`. This restricted runtime requires the PostgreSQL and
Backblaze Podman secrets so it can remove disposable demo documents before it
replaces the database baseline. It does not require Resend or browser-session
configuration because the finite reset job neither sends email nor serves
browser requests. The public API continues to use `APP_ENV=production` and
retains all production-mode security validation.

Container health belongs to the API Quadlet rather than the image. The API
Containerfile therefore has no Docker-format `HEALTHCHECK`; the generated
systemd service supplies the HTTP health command and waits for `healthy` before
reporting the API as started. The reset is a finite oneshot job and has no
health-check loop.

## Tests

```bash
uv run pytest
```

When `uv sync` creates or changes `uv.lock`, commit the lock file with the
dependency manifest. Do not substitute the globally installed Python for this
project environment.

Deployment and server installation are intentionally outside this directory.

## Incident reporting

`POST /api/v1/incidents` creates an authenticated, idempotent, privacy-minimized
client report only after the user selects **Report for investigation**.
`POST /api/v1/incidents/{id}/report` sends an already-protected server reference.
Unexpected server exceptions keep a diagnostic reference but do not email anyone
automatically. Resend sends separate Admin and Developer messages; non-secret
recipients are in the Quadlet and the API key remains a Podman secret.

The hosted demo can remove stored incident reports and their incident audit events
without resetting other data:

```bash
podman exec bridge-ph-pimascor-demo-api python -m pimascor_api.incident_admin purge --confirm DELETE-DEMO-INCIDENTS
```

The command refuses any deployment tier other than `demo`. It cannot remove journald
logs or email already accepted by Resend.
