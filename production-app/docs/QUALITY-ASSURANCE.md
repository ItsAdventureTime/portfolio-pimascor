# Quality assurance release acceptance

Use this checklist for each demo release and before any production release.
It distinguishes source checks from evidence captured against the deployed
application. Do not mark a release production-ready when an entry is skipped.

For the current demo-only entry and role-testing behavior, use
`DEMO-BUILD-SOURCE-OF-TRUTH-2026-08-08.md` when this older checklist conflicts.

## Local source gate

Run these from the repository before transfer:

```bash
(cd apps/api && uv sync --extra dev && uv run pytest -q)
(cd apps/web && pnpm build)
```

`uv sync` resolves the exact pinned package versions from `pyproject.toml` and
creates or refreshes `uv.lock`. Commit that lock file when it changes. If package
resolution is unavailable, record the API suite as **not run**; a successful web
build does not substitute for API verification.

## Deployed role acceptance

Use approved synthetic demo accounts. Record the exact account name, timestamp,
and outcome, but never place passwords or email codes in this document, a ticket,
or a command history.

| Role | Required proof |
| --- | --- |
| Requester | Can create and submit only its own draft Budget Request, cannot view DCS payment proof or Shipment Profitability, and receives a forbidden result for another Requester's draft. |
| Mich | Can review a submitted Budget, manage permitted Billing/Liquidation work, and cannot make GM or DCS decisions. |
| GM | Can approve or return pending approved-work queues and may use an exceptional DCS Payment override only with a reason of at least 10 characters; verify its distinct `GM_PAYMENT_OVERRIDE` audit action. |
| DCS | Can record a payment only with an active configured funding source, can hold/return/note, and cannot create arbitrary sources. |
| Admin | Can administer funding sources, tax profiles, and activity; still cannot bypass CSRF, evidence, version, finalization, or confirmation controls. |

The demo login must visibly offer **Login as Admin** / **Enter demo as Admin**,
and the authenticated Admin controls must expose the Requester, GM, DCS, and
Mich workspaces for evaluation without changing the authenticated identity.

For each attempted forbidden action, verify a `403` or the equivalent explicit
permission message. For each state-changing action, verify the resulting record
state and attributable history before continuing.

## Responsive and browser-engine acceptance

Test an authenticated workflow at these minimum viewports:

| Viewport | Required checks |
| --- | --- |
| 1280 × 720 | Sign-in has no nested scrollbar; Payment Center and record tabs have no unintended scrollbar; print preview opens. |
| 390 × 844 | No horizontal page overflow; navigation is operable; tabs reflow without clipping; forms and dialogs remain usable. |

On narrow login screens, the sign-in card must be the first useful content in
the viewport; the brand story may follow it without requiring a long scroll
before authentication. Confirm the page still has vertical-only scrolling and
that reduced-motion preferences suppress non-essential transitions and
animations.

Run the same smoke path in current Chromium/Blink, Firefox/Gecko, and
Safari/WebKit. Check sign-in, navigation, one read-only record, one authorized
role action, one forbidden role action, quotation print preview, and protected
document viewer. Record the browser version and pass/fail result. Do not infer
WebKit or Gecko support from a Chromium run.

## Public demo release evidence

After VPS activation and before any Bunny purge:

1. Confirm the public health endpoint responds successfully.
2. Record the release commit and expected fingerprinted CSS/JavaScript assets
   printed by the VPS updater. Confirm the public `index.html` references those
   exact assets after any required targeted Bunny purge.
3. Confirm the current UI contains the deployed scrollbar and responsive fixes.
4. Confirm Accounting Export shows separate Billing CSV and Collections CSV.
5. Confirm the complete local-record archive message says the feature is disabled
   in the demo and does not send mail or create a download.
6. Purge only the documented mutable URLs when the updater reports an older
   public index, then repeat every public-route check.

## Evidence classification

Follow [Factual basis and evidence policy](FACTUAL-BASIS.md). Local build/test
results prove local source only. VPS command output proves VPS activation.

### Password recovery acceptance

- Submit reset for active, disabled, pending, and unknown identifiers; verify the
  same response shape/message and no account disclosure.
- Confirm the eligible account receives a reset email whose fragment link contains
  no query-string token, expires in 15 minutes, works once, and is not logged.
- Verify wrong tokens increment the attempt counter and the fifth wrong attempt
  invalidates the request; expired and reused links fail generically.
- Require a 12-character password and matching confirmation; confirm the old
  password fails, the new password works through normal password-plus-email-code
  sign-in, every prior session is revoked, and audit events contain no secrets.
- Repeat on Chromium/Blink, Firefox/Gecko, and Safari/WebKit desktop and mobile
  viewports; verify keyboard focus, screen-reader labels, and no horizontal scroll.
- After authentication, on Android Chrome verify the native install action when
  available. On iPhone/iPad Safari, verify the manual Share → Add to Home Screen
  instructions. Confirm the reminder is dismissible for 14 days, disappears in
  standalone/fullscreen/minimal-ui/window-controls-overlay modes, does not appear
  on the login screen, and never blocks workflow use.
- Sign in with a user who has not acknowledged the current release and verify the
  dated **What's new in PIMASCOR** dialog appears once, explains user benefits,
  and records acknowledgement. Sign in again and confirm it does not repeat;
  verify a different user still receives it once. Close the dialog during a
  simulated acknowledgement failure and confirm the workspace remains usable;
  the announcement should return on the next login.
Browser observations prove only the tested route, account, viewport, and engine.

## Audit evidence: 2026-08-03

The local isolated audit used the development API with a disposable SQLite
database and synthetic accounts. The API suite passed **70 tests**; Python
compilation and the full Alembic chain through `20260803_0014` also passed.
The web TypeScript/Vite build passed with Vite 8.1.5. Chromium/Blink was
exercised at desktop 1280 × 720 and mobile 390 × 844. Both viewports had no
horizontal overflow, the installation guide opened in a bounded mobile dialog,
and the browser console had no errors or warnings.

A responsive follow-up also exercised 1440 × 900, 1280 × 720, 1024 × 768,
390 × 844, and 360 × 800. Every viewport had `scrollWidth` equal to the
document client width and no overflowing element. At the stacked tablet and
phone breakpoints, the sign-in card now appears before the supporting hero
content; recovery and first-time activation controls remained reachable, and
the browser console stayed clear of errors and warnings.

The API test run still reports Starlette's upstream deprecation warning for its
legacy `httpx` TestClient import. It is test-tooling-only and does not affect
the deployed API; keep it visible until the upstream-compatible client path is
available in the pinned dependency set.

The audit fixed canonical routing for restricted roles: Requester now lands on
Sales Quotations and the URL is `#quotations`, rather than leaving `#dashboard`
while silently rendering the fallback page. The same first-permitted-page rule
is used for role preview and protected deep links.

Firefox/Gecko, Safari/WebKit, the real VPS, production email delivery, Caddy,
object storage, and external CDN cache behavior were not exercised in this
isolated run. Treat those checks as required release evidence before production
deployment; do not infer them from the Chromium result.
