# PIMASCOR demo implementation handoff

ACTIVE_ROLE: implementation complete; independent review pending
NEXT_OWNER: GPT-6 Sol (High), independent review of the published candidate
IMPLEMENTATION_OWNER: GPT-6 Luna (High)
REVIEW_OWNER: GPT-6 Sol (High), separate follow-up turn
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
  commit at publication. Independent review remains pending.

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
2. Keep only safe non-secret values in Compose. Keep credentials in ignored
   files outside the checkout and mount per service. No `.env`. Prove UID 10001
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
