# Quality assurance release acceptance

Use this checklist for each demo release and before any production release.
It distinguishes source checks from evidence captured against the deployed
application. Do not mark a release production-ready when an entry is skipped.

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

For each attempted forbidden action, verify a `403` or the equivalent explicit
permission message. For each state-changing action, verify the resulting record
state and attributable history before continuing.

## Responsive and browser-engine acceptance

Test an authenticated workflow at these minimum viewports:

| Viewport | Required checks |
| --- | --- |
| 1280 × 720 | Sign-in has no nested scrollbar; Payment Center and record tabs have no unintended scrollbar; print preview opens. |
| 390 × 844 | No horizontal page overflow; navigation is operable; tabs reflow without clipping; forms and dialogs remain usable. |

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
- On Android Chrome, verify the native install action when available. On iPhone/iPad
  Safari, verify the manual Share → Add to Home Screen instructions. Confirm the
  reminder is dismissible for 14 days, disappears in standalone mode, and never
  blocks sign-in or workflow use.
Browser observations prove only the tested route, account, viewport, and engine.

## Audit evidence: 2026-08-01

The local isolated audit used the development API with a disposable SQLite
database and synthetic accounts. `uv run pytest -q` passed **65 tests** in both
the normal test tier and `DEPLOYMENT_TIER=production`; `pnpm build` passed with
Vite 8.1.5. Chromium/Blink was exercised at desktop 1440 × 900 and mobile
390 × 844. Admin, GM, DCS, Mich, and Requester sign-in flows completed with
email-code verification; each role displayed only its permitted navigation.
The mobile check showed no horizontal overflow, and the browser console had no
errors or warnings.

The audit fixed canonical routing for restricted roles: Requester now lands on
Sales Quotations and the URL is `#quotations`, rather than leaving `#dashboard`
while silently rendering the fallback page. The same first-permitted-page rule
is used for role preview and protected deep links.

Firefox/Gecko, Safari/WebKit, the real VPS, production email delivery, Caddy,
object storage, and external CDN cache behavior were not exercised in this
isolated run. Treat those checks as required release evidence before production
deployment; do not infer them from the Chromium result.
