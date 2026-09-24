# PIMASCOR demo implementation handoff

ACTIVE_ROLE: local runtime secrets prepared; OrbStack and public acceptance still unverified
NEXT_OWNER: implementation agent to finish optional R2 wiring and OrbStack checks after owner supplies Cloudflare details; independent reviewer to complete public acceptance
IMPLEMENTATION_OWNER: GPT-6 Luna (High)
REVIEW_OWNER: GPT-6 Sol (Medium), current follow-up turn
TARGET: `https://pimascor.delegateops.business`
GIT_TARGET: `https://github.com/ItsAdventureTime/portfolio-pimascor.git` over HTTPS
PUSH_CAPABILITY: signed local commit and guarded non-force push after checks
DEPLOYMENT_CAPABILITY: demo only; use owner's existing OrbStack/Tunnel, never production

## Start here

## Takeover progress — 2026-09-24

- The handoff estimated 24 prior worktree entries; takeover showed 40 paths
  with staged, unstaged, or untracked changes. They remain intact and are
  being reviewed as prior in-progress work.
- Official Docker, PostgreSQL image, and Cloudflare R2 documentation was
  checked. The canonical Compose file now pins PostgreSQL 18.6 Alpine 3.23 by
  multi-platform manifest digest and mounts its volume at
  `/var/lib/postgresql`.
- The manual runbook now distinguishes source guidance from runtime evidence
  and blocks startup on missing secrets, unreadable UID probes, or Tunnel
  network prerequisites. It identifies document upload/view as incomplete
  until private R2 setup and tests pass.
- The expected OrbStack runtime directory and secrets do not exist on this
  host. R2 activation/credentials and existing Tunnel state have not been
  verified. No container startup or public URL claim is authorized by this
  evidence; continue source checks and record the owner actions required.
- API tests, demo web build, ARM64 image build/inspection, Compose source
  configuration assertions, implementation notes, and focused path review are
  complete. Signed commit `5675ec0b9d08a38dfb883c71178d968cce500332` was
  verified locally and pushed to the public HTTPS remote. GitHub reports
  `unknown_key` for its signature; the available CLI token lacks the scope to
  inspect registered signing keys. The remote main SHA matched the local
  commit at publication. Independent review was pending at that point.

Read [the hosting decision and manual operator guide](../../production-app/docs/DEMO-HOSTING-DECISION-2026-09-24.md),
then the current
[Compose runbook](../../production-app/infra/docker-compose/README.md),
[demo source of truth](../../production-app/docs/DEMO-BUILD-SOURCE-OF-TRUTH-2026-08-08.md),
[quality checks](../../production-app/docs/QUALITY-ASSURANCE.md), and
[post-change checklist](../../production-app/docs/POST-CHANGE-SYNC-CHECKLIST.md).
This handoff and the hosting decision govern this demo hosting task. Production
runbooks and Quadlets remain separate.

At planning time, `main` was `979fb0e41c6caec1949daedbcaff1eb8e97c8ceb`.
There were 24 existing staged/unstaged/untracked worktree entries, including
in-progress Compose, API, web, test, and runbook changes. Treat them as
someone else's work until inspected; do not reset, overwrite, or stage them
indiscriminately. Recheck status and diffs on takeover. This handoff does not
assert those edits pass tests or are deployed.

## Build the smallest complete demo

1. Finish the existing `production-app/infra/docker-compose/compose.yaml`
   path. Keep one API image serving the built web app, one PostgreSQL service,
   a named DB volume, no host port, and the existing external
   `cloudflared-network`. Do not create another `cloudflared` service. Pin the
   PostgreSQL image and validate the correct volume path for that major.
2. Keep only safe non-secret values in Compose. Keep credentials in the ignored
   `.runtime/pimascor-demo/secrets/` folder and mount per service. No `.env`. Prove UID 10001
   can read API secrets and PostgreSQL can read its password with mode/ownership
   that does not expose them to other Mac users. Compose file secrets do not
   remap UID/GID; do not solve this with `chmod 644`.
3. Build frontend with demo flags and root paths. Preserve server-side demo
   entry, role enforcement, session/CSRF protections, private API caching,
   synthetic records, and disabled full archive. Migration, initializer, and
   reset run manually, never on API restart. Keep `APP_ENV=production` security
   checks while `DEPLOYMENT_TIER=demo` enables only demo behavior.
4. Make document upload and protected inline view functional through private
   R2 S3 API, if the owner has activated R2 and supplied scoped credentials.
   Reuse `services/storage.py`'s boto3 client; limit config changes to the
   demo storage contract and preserve production B2 restrictions. Do not
   expose the bucket publicly. If R2 is unavailable, isolate the blocked
   document flows and report the demo as incomplete.
5. Update only directly affected demo runbooks/indexes and code tests. Use
   `jk-sbx-project implement` for project builds/tests and changes in the
   primary worktree. No host project execution, no second validation stack.
   Signed commit and push only reviewed paths via the public portfolio HTTPS
   remote. Keep the existing unrelated index/worktree entries intact.

## Verification the implementer owns

- `git status --short --branch` and focused `git diff --check` before commit.
- API unit suite and web TypeScript/Vite build in `jk-sbx-project implement`.
  Exercise one demo reset regression: data persists through API restart and
  resets only after explicit reset. Check storage upload/range/delete/reset
  path with R2 when configured.
- `docker compose config --quiet`, image architecture, no host `ports:`, DB
  health, API health, non-root secret-read check, explicit migration/seed/reset,
  and a bounded request through `cloudflared-network` on OrbStack.
- Record exact commands, exit codes, release SHA/image digest, failed checks,
  and any conservative deviation in [implementation notes](HANDOFF.notes.md).

Independent review by GPT-6 Sol (High) owns public URL, rendered browser and
viewport checks, console/accessibility acceptance, role/security negative
paths, Cloudflare cache/Tunnel observations, and a final check that the
published Git SHA matches local. Use `jk-sbx-project validate` for independent
source checks against a committed snapshot; that lane cannot see uncommitted
files or the implementation worktree's dependencies.

## Stop conditions

- If current `main`, tracked files, or user edits differ materially from this
  handoff, inspect and update the plan before implementation; never discard
  them to force the plan through.
- If the target public repo no longer shares local `main` ancestry, stop the
  push and report both SHAs. No force push or history rewrite.
- If secret files cannot be read by the intended non-root processes without
  weakening their Mac permissions, stop startup and report the permission
  evidence. Do not place secrets in Compose or image layers.
- If the existing Tunnel or network cannot be identified, leave its other
  hosted apps untouched and request the exact runtime details from the owner.
- If R2 credentials/activation are unavailable, stop the document acceptance
  claim, not the rest of the implementation. Report the missing manual step.

## Finish line

Hand back to the GPT-6 Sol reviewer with a committed, documented candidate,
checks and notes. Only report a fully functional public demo after the external
URL and protected document path pass independent review. If a true external
blocker remains, name it and the smallest owner action needed. Do not claim
Cloudflare Workers, R2, OrbStack, Tunnel, or public deployment succeeded from
source files alone.

## Independent review — 2026-09-24

Reviewed committed `b1baa0d1a5a66c229e0be201ed7a47bc744daf37` against
this handoff, the demo source of truth, the Compose runbook, and the changed
source. **Verdict: source checks conditionally pass; public demo acceptance
fails.** No deployment or secret/Tunnel/R2 change was made.

- **P1 — runbook secret probe (resolved in `4f649cde`).**
  `production-app/infra/docker-compose/README.md:98-99` overrides the
  PostgreSQL entrypoint with `/bin/sh`. The original command returned UID 0.
  The corrected command adds `--user 70:70`; independent Compose validation
  returned UID 70 and read a disposable placeholder secret. Actual OrbStack
  file readability remains unverified.
- **P1 — runtime acceptance unavailable.** The expected
  `~/docker/portfolio/pimascor/` folder is absent, and the public hostname
  failed DNS resolution (`curl` exit 6). No DB/API health, Tunnel route, role,
  browser, cache, R2 document, or restart-persistence claim can pass yet.
- **P2 — GitHub signature status unresolved.** Local `git verify-commit HEAD`
  passed and remote `main` matches local HEAD, but GitHub reports
  `verified: false`, reason `unknown_key`. The owner must register the signing
  key with GitHub, or otherwise resolve GitHub verification, before the
  post-change signature gate is complete. Git transport is HTTPS.
- **P3 — stale planning wording (resolved in `4f649cde`).**
  `production-app/docs/DEMO-HOSTING-DECISION-2026-09-24.md:13-17` now says
  the implementation is published and clearly separates source publication
  from deployment evidence.

Independent validation used only `jk-sbx-project validate` on the committed
snapshot: `uv sync --locked --extra dev` and `uv run --locked pytest -q`
passed; `npm ci` and the demo Vite build passed; `docker compose config
--quiet` passed. The pinned PostgreSQL image UID probe returned `0` and `70`
for the shell and `postgres` account. `git diff --check 979fb0e..HEAD` passed.
`npm audit` reported one high `nanoid` and one moderate `postcss` advisory;
`npm audit --omit=dev` reported zero. API tests retained the Starlette
deprecation warnings recorded in implementation notes. No source defects
were found beyond the runbook probe; document storage remains incomplete
without private R2 configuration and live checks.

## Implementor response — 2026-09-24

- Fixed the PostgreSQL secret probe to set `--user 70:70` before overriding
  the image entrypoint. The pinned image reproduced UID 0 without that option
  and UID 70 with it. A temporary Compose fixture with a placeholder secret
  passed the corrected UID/readability command. This does not prove actual
  OrbStack secret file permissions; the owner must still run that probe on the
  real files before database startup.
- Updated the hosting decision to remove stale “uncommitted” wording and
  record the reviewer-observed DNS failure without treating source publication
  as deployment evidence.
- Remaining blockers: expected OrbStack secrets/runtime folder is absent,
  public DNS fails, R2 acceptance is unverified, and GitHub reports
  `unknown_key` for the locally verified SSH signature. The reviewer
  independently rechecked the corrected probe and documentation in commit
  `4f649cde570b77030299460474fc1bd96776c055`; both findings are resolved.

## Reviewer follow-up — 2026-09-24

Committed `4f649cde570b77030299460474fc1bd96776c055` resolves the original
P1 probe and P3 wording findings above. `jk-sbx-project validate` ran the
updated `docker compose run --user 70:70 --entrypoint /bin/sh db` against the
pinned PostgreSQL image with a disposable placeholder secret: exit 0, UID 70,
file readable. This proves the command form only; it does not prove ownership
or readability of absent OrbStack runtime files. The runbook and hosting
decision diff passed `git diff --check`.

The P1 runtime/DNS and P2 GitHub signature blockers remain. The public DNS
request was not repeated. Local `git verify-commit HEAD` passed; GitHub's
`main` SHA matches `4f649cde570b77030299460474fc1bd96776c055` and still
reports `verified: false`, reason `unknown_key`. **Verdict remains: source
checks conditionally pass; public demo acceptance fails.**

## Current independent review — 2026-09-24

Reviewed clean `main` at `73a933da9017af2b142119b3b25e5f7d7480ab8a`.
The two commits after `4f649cde` change documentation only. In a fresh
`jk-sbx-project validate` snapshot, `uv sync --locked --extra dev` and
`uv run --locked pytest -q` passed (all tests; two Starlette deprecation
warnings). `npm ci --silent` and the demo TypeScript/Vite build passed with
`VITE_BASE_PATH=/`, `VITE_API_URL=/api/v1`, the demo CSRF cookie name, and
`VITE_DEPLOYMENT_TIER=demo`. The unchanged Compose source and disposable
UID-70 probe retain the prior review's passing result; no real runtime
secret-read check was possible.

The public `/api/v1/health` request still exits 6 because
`pimascor.delegateops.business` does not resolve. The expected OrbStack
runtime directory is absent. Local `git verify-commit HEAD` passes and GitHub
`main` matches `73a933da9017af2b142119b3b25e5f7d7480ab8a`, but GitHub
reports `verified: false`, reason `unknown_key`. No live DB/API, Tunnel,
browser, role, cache, restart-persistence, or R2 document check has passed.
**Verdict: source checks pass; public demo acceptance remains blocked.**

Next implementation agent: after the owner supplies the external runtime and
Tunnel details, prove UID 10001/70 can read only their assigned secrets,
load the reviewed ARM64 image into OrbStack, start DB, run migration,
initializer, and reset explicitly, then start API and record health and
restart-persistence results. If full document behavior is required, add
private R2 configuration and test upload, protected range view, delete, and
reset cleanup before claiming it works. Record exact commands and results in
`HANDOFF.notes.md`; hand public URL, role, browser, and cache acceptance to
an independent reviewer. Resolve GitHub's signing-key registration separately.

## Runtime preparation and remaining work — 2026-09-25

- Created `production-app/infra/docker-compose/.runtime/pimascor-demo/` in
  the workspace. It contains the current Compose copy, a newly generated
  64-character hexadecimal PostgreSQL password, and a matching database URL.
  The secrets directory is mode `0700`; both credential files are mode `0600`.
  A local check confirmed the URL and password match without printing either.
  Git ignores the entire runtime folder, and the Docker build context excludes
  it. Existing legacy files under `infra/docker-compose/secrets/` were left
  untouched. The generated pair is for a fresh DB volume only.
- Four R2 input placeholders sit in the ignored runtime secrets directory.
  They are not mounted. The owner must supply a private R2 bucket, scoped S3
  access key pair, and account endpoint. Current Compose and application
  storage validation still need demo-specific R2 wiring before document
  acceptance can pass. Preserve the production B2 settings.
- Updated the public Compose guide with workspace-local secret preparation,
  image transfer, volume and UID checks, Tunnel routing, public checks, and
  rollback. The hosting decision points to the same runtime folder.
- Public `/api/v1/health` still fails DNS resolution (curl exit 6). OrbStack
  volume, network, image, and secret mounts have not been inspected. The host
  Docker control commands were rejected by the execution boundary, which
  requires project Docker work through `jk-sbx-project`; its isolated
  validation lane cannot inspect OrbStack. No startup or deployment occurred.

Next implementation checks: first inspect whether
`pimascor-demo_demo_postgres_data` already exists. If it does, do not start
PostgreSQL with the new password until credentials and data are reconciled.
Prove Compose can mount each secret for UID 10001 and UID 70 without making
files readable to other Mac users. Then complete the manual startup and R2
checks in the updated runbook. The owner must repair DNS/Tunnel routing and
register the existing Git signing key with GitHub. Public browser and role
acceptance follows only after a reachable deployment.
