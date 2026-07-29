# PIMASCOR Web Application

This is the React browser application. Authentication, clients, Budget Requests and Additional Budgets, GM Approval, the DCS for Payment queue, Mich-owned Requests for Payment, Liquidations, Billing, and Client Payments use the FastAPI service.

## Requirements

- The active Node.js LTS release
- npm

## Run locally

```sh
npm install
npm run dev
```

Start the API first, then open the local address printed by Vite, normally `http://localhost:5173`. The default API is `http://127.0.0.1:8000/api/v1`; override it with `VITE_API_URL` when needed.

## Validate a production build

```sh
npm run build
npm run preview
```

## Export the hosted static site with Podman

The hosted deployment does not run a frontend web-server container. The
Containerfile uses the official `node:lts-alpine` channel only as a temporary
build stage, then exports the compiled files for the existing Caddy container
to serve directly. The moving LTS alias is appropriate here because Node never
runs in the deployed application and every rebuilt artifact is validated before
it replaces the current site:

```sh
podman build --pull=always --output type=local,dest="$HOME/bridge-ph/pimascor-demo/web-dist" --build-arg VITE_BASE_PATH=/pimascor/demo/ --build-arg VITE_API_URL=/pimascor/demo/api/v1 --build-arg VITE_CSRF_COOKIE_NAME=bridge_ph_pimascor_demo_csrf .
```

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

Local form errors and important warnings use `ActionMessageDialog.tsx`: a centered,
focus-managed `alertdialog` with a specific corrective action. Successful and
ordinary informational confirmations remain non-blocking status toasts.
