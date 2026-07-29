# Local records exports

## Decision

Use the existing private Backblaze B2 S3-compatible storage for completed ZIP archives. Do not place the generated archive on the API server filesystem and do not use a public Bunny CDN URL for it. The API keeps the bucket private and streams a download only after the signed-in Administrator is authorized; the notification email takes the user to the authenticated Accounting Export page, not to a bearer URL.

Backblaze B2 should have bucket-default SSE-B2 (AES-256) enabled before production use. Archive object keys contain only generated IDs, never a client, staff, or shipment name. The production key must be restricted to the configured bucket/prefix and allow only the object operations required by the worker and API.

## Archive contents

- `records/*.csv`: UTF-8, comma-separated operational records per module. These include quotations, budgets, releases, expenses, liquidations, billing, collections, allocations, credit memos, audit events, and users without password hashes.
- `attachments/*`: the original uploaded PDF/JPEG/PNG evidence and signed quotations, retained in their original usable formats.
- `README.txt`: archive scope and exclusions.

The archive deliberately excludes password hashes, live sessions, email verification challenges, and storage credentials. It is a portable operational-records copy, not a general-ledger import and not a replacement for a tested disaster-recovery backup.

## Controls

- Only an Administrator can request, see, or download an archive.
- The quota is two accepted archive requests per organization per Philippine calendar week. It applies to requests, not download attempts, so a ready archive can be retried during its availability window.
- A single worker processes durable queued requests. It must run as one dedicated replica using `python -m pimascor_api.export_worker`; this is intentionally separate from the API process so a restart does not abandon the work.
- Completion creates an auditable archive, sends the requester an email, and makes it available for exactly one hour. The worker deletes expired objects and records the expiry.
- The API keeps downloads same-origin, authenticated, `no-store`, and audited. No direct signed URL is mailed or exposed.

## Deployment checklist

1. Apply Alembic revision `20260729_0011`.
2. Enable B2 bucket-default SSE-B2 and keep the bucket private.
3. Deploy one `pimascor_api.export_worker` process with the same database, B2, and email secrets as the API, but no inbound public port.
4. Ensure the worker remains up continuously. Its 30-second idle poll performs expiration cleanup; B2 lifecycle policies are only a secondary safety net because their smallest cadence is daily.
5. Have the DPO approve the retention wording, authorized-admin list, and procedure for encrypted removable media before rollout.

## Sources

- [National Privacy Commission: Data Security](https://privacy.gov.ph/data-security/)
- [National Privacy Commission: Right to Data Portability](https://privacy.gov.ph/right-to-data-portability/)
- [Backblaze B2 server-side encryption](https://www.backblaze.com/docs/cloud-storage-server-side-encryption)
- [OWASP Secure Cloud Architecture Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secure_Cloud_Architecture_Cheat_Sheet.html)
