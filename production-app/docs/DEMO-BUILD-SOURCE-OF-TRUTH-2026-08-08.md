# Demo build source of truth — 2026-08-08

This document is the newest demo-only interpretation of the PIMASCOR project
documentation. It supplements, and where necessary supersedes, older product
specifications, requirements, handoff snapshots, and generated client-packet
PDFs. Production behavior is not changed by these demo defaults.

Use `DEMO-DOCUMENTATION-INDEX.md` for the complete demo file map and release
sequence.

## Demo entry behavior

- Demo controls are compiled only when `VITE_DEPLOYMENT_TIER=demo` (or the
  explicitly equivalent `VITE_APP_ENV=demo`) is supplied. Missing markers fail
  closed, so a URL path alone never enables demo behavior.
- The demo sign-in screen visibly offers **Enter demo as Admin** as the primary
  evaluation path and does not request username, password, or OTP credentials.
- The button creates a normal server-side session only through the demo-tier
  endpoint. It remains an explicit user action, is auditable, and never appears
  in the production build.
- After entering the demo, the Admin workspace visibly exposes the documented
  Requester, GM, DCS, and Mich workspaces for evaluation.
- Switching workspaces is an attributable Admin testing mode. It does not create
  a second identity, change the signed-in account, reveal passwords, or bypass
  server-side authorization.
- The demo role switch is visible from the Admin controls and can be returned to
  the complete Admin workspace at any time.

## Demo capability baseline

- Admin, GM, DCS, and Mich can evaluate Shipment Profitability and the authorized
  Accounting Export workflows. Requester is not given Shipment Profitability in
  the current demo baseline.
- GM payment overrides are exceptional, require a reason of at least ten
  characters, and create `GM_PAYMENT_OVERRIDE_*` audit events.
- Signed quotations and uploaded supporting files use the protected viewer when
  a real stored object exists. Authorized staff may download through the audited
  download route; Requester remains view-only for protected payment evidence.
- The revised quotation reference remains a dynamic visual/terms reference, not
  a static data source.
- Complete local-record archive generation remains disabled in the demo. The
  production export worker and its B2/Resend secrets are not copied into demo
  Quadlets.

## Reconciliation rule

When an older document conflicts with this file, this file governs the demo
release. Keep older production-oriented requirements intact unless a newer
production decision explicitly changes them. Generated PDFs are delivery
snapshots and must be regenerated before a client handoff if their wording is
intended to describe this demo revision.

## Evidence required before CDN purge

Run the local transfer command, then the VPS activation command in
`docs/DEMO-VPS-DEPLOYMENT.md`. Verify the deployed commit, health endpoint,
Admin entry, visible role switch, role-specific gates, quotation preview, and
protected document viewer before purging mutable Bunny URLs.
