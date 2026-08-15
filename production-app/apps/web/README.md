# PIMASCOR Web Application

This is the React browser application. Authentication, clients, Budget Requests and Additional Budgets, GM Approval, the DCS for Payment queue, Mich-owned Requests for Payment, Liquidations, Billing, and Client Payments use the FastAPI service.

## Requirements

- Docker Sandbox with `jk-sbx-project`
- Node.js and npm inside the project Sandbox

## Run locally

```sh
jk-sbx-project exec sh -lc 'cd production-app/apps/web && npm ci'
jk-sbx-project exec sh -lc 'cd production-app/apps/web && npm run dev -- --host 0.0.0.0'
```

Run these commands from the repository root. Start the API first, then open the
local address printed by Vite, normally `http://localhost:5173`. The default API
is `http://127.0.0.1:8000/api/v1`; override it with `VITE_API_URL` when needed.

## Validate a production build

```sh
jk-sbx-project exec sh -lc 'cd production-app/apps/web && npm run build'
jk-sbx-project exec sh -lc 'cd production-app/apps/web && npm run preview -- --host 0.0.0.0'
```

## Build the hosted release locally in Docker Sandbox

The hosted deployment does not run a frontend web-server container. The
Containerfile uses a verified immutable Node build image digest for its
temporary build stage, then exports the compiled files for the existing Caddy
container to serve directly. Node never runs in the deployed application, and
every release artifact is built locally before it is transferred to the VPS.

From the repository root, use the release builder. It calls
`jk-sbx-project exec` for the API image and the static PWA, then writes
`api-image.tar`, `web-dist/`, and a release manifest to the ignored output
directory:

```sh
production-app/infra/scripts/build-local-release.sh \
  --tier demo \
  --commit "$(git rev-parse HEAD)" \
  --output-dir production-app/.deployment-artifacts.demo.manual
```

Use `--tier production` for the production base path and API route. Do not run
`podman build` on the Mac or on the VPS. The VPS updater loads the transferred
API image archive and stages the transferred static files; it does not compile
or build them.

Use the maintenance procedure in `../../infra/README.md` when replacing an
already deployed build. It stages and validates the new files before Caddy is
reloaded.

## Connected walkthrough

1. Sign in with the administrator created by the API seed command.
2. Complete the email-code check; development displays the local code on screen.
3. As Requester, create and submit a Budget Request or linked Additional Budget.
4. As GM, decide it in the consolidated Approval Center.
5. As DCS, pay, hold, return, or annotate it in DCS for Payment.
6. As the Requester, enter actual expenses and receipt evidence for Liquidation.
7. As Mich, attach the required proof and close the Liquidation.
8. As Mich, create a Request for Payment (OPEX, Marketing, Loan Payment, or Other), prepare and finalize Billing, and record a Client Payment against one or more Billing records.

## Current boundary

The seeded records are fictional and are reset by the scheduled demo reset. Verified
PDF/JPEG/PNG documents are transferred privately to Backblaze B2 and remain
authorization-controlled. Accounting export is CSV-first while the exact
accounting/tax mapping remains a business decision. The server enforces authorization
on every connected action.

Every signed-in role also receives the shared accessible incident dialog. It explains
the problem, suggests recovery, and offers exactly two choices: dismiss locally
without reporting, or report privacy-minimized context to Bridge PH Admin and the
Developer for investigation.

Local form errors, warnings, successful confirmations, and ordinary informational
results use `ActionMessageDialog.tsx`: a centered, focus-managed `alertdialog`
with a specific corrective action or deliberate Close and continue action. The
application does not use disappearing status toasts.

Support questions, suggestions, and ordinary help requests use the compact,
responsive topbar dialog defined in `../docs/SUPPORT-TICKETS.md`. It keeps
ticket details in the same dialog instead of taking over a full page. Production
creates durable tickets and emails Alyssa and JK; demo uses simulated replies
without email.
