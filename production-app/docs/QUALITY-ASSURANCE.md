# Quality assurance release acceptance

Use this checklist for each demo release and before any production release.
It distinguishes source checks from evidence captured against the deployed
application. Do not mark a release production-ready when an entry is skipped.

## Local source gate

Run these from the repository before transfer:

```bash
(cd apps/api && uv sync --extra dev && uv run pytest)
(cd apps/web && npm run build)
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
| Requester | Can create and submit only its own draft Budget Request, cannot view DCS payment proof, and receives a forbidden result for another Requester's draft. |
| Mich | Can review a submitted Budget, manage permitted Billing/Liquidation work, and cannot make GM or DCS decisions. |
| GM | Can approve or return pending approved-work queues, and cannot record an actual DCS payment. |
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
2. Confirm the current UI contains the deployed scrollbar and responsive fixes.
3. Confirm Accounting Export shows separate Billing CSV and Collections CSV.
4. Confirm the complete local-record archive message says the feature is disabled
   in the demo and does not send mail or create a download.
5. Purge only the documented mutable URLs after the preceding checks pass.

## Evidence classification

Follow [Factual basis and evidence policy](FACTUAL-BASIS.md). Local build/test
results prove local source only. VPS command output proves VPS activation.
Browser observations prove only the tested route, account, viewport, and engine.
