# PIMASCOR Production Application

This directory is the working root for the new PIMASCOR Operational Control System.

## Current documents

- `PLAN.md`: approved product, architecture, security, migration, testing, and delivery plan
- `docs/MEETING-DECISIONS-2026-07-24.md`: controlling owner-meeting decisions and scope
- `docs/REQUIREMENTS-V2.md`: consolidated role, terminology, workflow, and acceptance baseline
- `docs/PRODUCT-SPEC.md`: detailed UI, behavior, validation, and permissions
- `docs/USER-FLOWS.md`: Requester, GM, DCS, Mich, Admin, and identity journeys
- `docs/DESIGN-SYSTEM.md`: PIMASCOR visual and accessibility rules
- `docs/DATA-MODEL.md`: conceptual production entities and constraints
- `docs/API-CONTRACT.md`: planned FastAPI resource contract
- `docs/PHASE-0-REVIEW.md`: operational owner review and sign-off checklist
- `docs/REVISION-2026-07-23.md`: screenshot-by-screenshot implementation map and remaining production boundaries
- `docs/UX-PHILIPPINE-CONTROLS.md`: current UX/accessibility and Philippine VAT/CWT design basis with primary references
- `docs/INCIDENT-REPORTING.md`: shared error detection, recovery, privacy, notification, and audit contract
- `docs/FACTUAL-BASIS.md`: evidence labels, confirmed VPS layout, and rules against presenting assumptions as facts
- `docs/QUALITY-ASSURANCE.md`: required role, responsive, browser-engine, and deployment acceptance evidence
- `docs/PRODUCTION-BACKUP-RESTORE-RUNBOOK.md`: encrypted backup catalog and owner-only CLI dry-run restore procedure
- `docs/HANDOFF-BRIDGE-PIMASCOR.md`: internal production handoff boundary, acceptance, and source/IP terms
- `docs/POST-CHANGE-SYNC-CHECKLIST.md`: required research, documentation sync, signed commit, HTTPS publication, and remote verification workflow
- `handoff/bridge-pimascor/client-packet/`: current client-facing handoff PDF and delivery manifest
- `docs/DEMO-BUILD-SOURCE-OF-TRUTH-2026-08-08.md`: newest demo-only Admin entry and role-evaluation rules
- `docs/SUPPORT-TICKETS.md`: production support tickets and demo simulation contract
- `docs/DEMO-DOCUMENTATION-INDEX.md`: starting point and file map for demo-only work
- `docs/CODEX-OPERATIONAL-WORKFLOW-FOUNDATION-PROMPT.md`: downloadable Codex foundation prompt for adapting the system to another industry
- `apps/web/`: React and Vite PWA with connected Shipment Profitability, GM-controlled Billing, professional A4 printing, view-only confidential documents, and the Admin-only Bridge PH Activity Monitor
- `apps/api/`: FastAPI application with PostgreSQL migrations, password plus email-code sign-in, API-enforced roles, GM approval gates, privacy-minimized audit/incident events, controlled payment sources, and financial workflow controls
- `infra/`: reviewed container definitions, rootless Quadlet templates, Caddy path handlers, and a command-by-command Fedora CoreOS team-demo runbook

## Next deliverables

1. Deploy the team-demo release at `/demo/pimascor/` by following `infra/README.md`; no host Python, Node.js, npm, or PostgreSQL installation is required. The Docker Sandbox builds the API image and static PWA locally, and the existing Caddy container serves the exported files directly.
2. Review the Phase 0 specification and hosted demo with each operational owner.
3. Record accepted changes and sign off the screen and workflow behavior.
4. Validate Shipment Profitability plus the connected GM approval, DCS payment, Additional Budget, Liquidation, Billing/replacement/Credit Memo, Client Payment, and Request for Payment workflows with each role owner.
5. Obtain Bridge Accounting decisions and approve malware scanning, document retention, monitoring policy, and production-only Backblaze credentials.
6. Complete server-retained archival PDF only if the business requires it, plus user/client administration, indexed search, centralized tamper-resistant log retention, production backup/restore rehearsal, and acceptance validation. The disposable demo is intentionally excluded from infrastructure backups.

## Run locally

The application currently uses two local processes. This is development setup, not VPS deployment.

1. Follow `apps/api/README.md` to create the pinned Python environment, migrate the database, seed the first administrator, and start the API on port 8000.
2. Follow `apps/web/README.md` to start the browser application on port 5173.
3. Sign in with the administrator you created. In development only, the email code appears in the API log and in the verification screen.

## Deployment boundary

This repository includes reviewed Containerfiles, Quadlet templates, Caddy path handlers, and a manual Fedora CoreOS runbook. Hosted deployments use no `.env` files: non-secret values stay in `.container` files and credentials are mounted from Podman secrets. The Mac-side transfer scripts build the API image and static PWA inside the Docker Sandbox, then transfer a commit-matched source and artifact bundle. The VPS performs plain artifact deployment and runtime activation; it does not compile or build. PostgreSQL 18 binds the exact `data/postgres/18/docker` directory. Caddy is the only public container. The public API uses the production security profile and Quadlet health checks. The 03:00 Asia/Manila maintenance job deletes objects below `pimascor/demo/documents/`, replaces disposable demo data locally, preserves accounts, and uses no backup restore. Production keeps separate credentials, the `pimascor/` object prefix, and the `pimascor/backups/restic/` repository.

The current production requirements source of truth is `docs/MEETING-DECISIONS-2026-07-24.md`, followed by `docs/REQUIREMENTS-V2.md` for implementation detail. The current demo-only source of truth is `docs/DEMO-BUILD-SOURCE-OF-TRUTH-2026-08-08.md`; it supersedes older demo wording and generated handoff snapshots. The meeting record supersedes older prototype assumptions. For deployment and operational claims, follow `docs/FACTUAL-BASIS.md`; never present an unverified VPS state as completed. Historical source prompts and generated snapshots are archived under the repository-root `not-needed/` boundary and are not active guidance.

For demo work, start with `docs/DEMO-DOCUMENTATION-INDEX.md`. Do not use the
production runbook, production Quadlets, or production secrets for the demo.
For the local-only NDA boundary and remote publication checks, read
`docs/REPOSITORY-EXPOSURE-AND-NDA.md`.
