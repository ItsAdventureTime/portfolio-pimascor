# Documentation and build consistency plan

This active phased plan keeps production and demo accurate. The builds share
reviewed product concepts but have separate runtime configuration, databases,
migration state, and release gates.

## Phase 1 — Establish the source of truth

Approved requirements and meeting decisions define intent. API contracts define
service boundaries. Product/UX specifications define visible behavior. Runbooks
define operations. Code and tests implement and prove those statements.

Analogy: establish the signed map legend before checking whether the roads on
the map actually exist.

## Phase 2 — Remove ambiguity

Obsolete prompts, inactive demo credentials, generated handoff snapshots, and
historical prototypes are outside the active analysis surface under root
`not-needed/`. They are provenance only and must not be read or used as
requirements unless historical recovery is explicitly requested.

Approved terminology includes Processor / Requester, Bridge Accounting as an
Admin-capability business label, own-shipment Requester profitability,
production audited downloads, demo inline-only viewing, and GM override in both
tiers.

Analogy: remove expired road signs from a warehouse before asking which sign to
follow.

## Phase 3 — Verify shared contracts

Check API schemas, migrations, role gates, audit behavior, email safety, demo
reset behavior, and frontend routes against active documentation. Support
tickets are distinct from incident reporting: production tickets are durable
and safely notify Alyssa and JK; demo tickets are synthetic and never send
production email or use production storage.

## Phase 4 — Verify production

Run API tests, frontend production build, migration/release checks, and
role/ownership evidence. Resolve mismatches before activation. Production
credentials remain valid and never enter docs or tests.

Analogy: inspect the real bridge using the approved load rating and checklist.

## Phase 5 — Verify demo

Run the same contract checks against demo, then separately verify synthetic
data, simulated support replies, inline-only documents, daily reset behavior,
demo migration state, and demo release safeguards.

Analogy: test the training bridge while confirming it cannot connect to the
real bridge or carry real cargo.

## Phase 6 — Synchronize and maintain

Update active docs, code, tests, Serena memories, local Git, and the authenticated
HTTPS GitHub mirror together. Use local `git` for commits and `gh auth
setup-git`, `gh auth status`, guarded HTTPS push, and `gh api` verification. Do
not use an SSH Git remote or SSH signing setup.

Every feature must update its contract, production behavior, demo behavior, QA
evidence, and deployment gate in the same change.
