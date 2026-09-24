# PIMASCOR production documentation map

This index is the starting point for any agent, operator, reviewer, or future
maintainer working on production. Demo documentation is intentionally separate
and must not be used as a production deployment instruction.

Start with [the consistency remediation plan](CONSISTENCY-REMEDIATION-PLAN.md)
for the phased review and maintenance workflow.

For demo-only work, start with `DEMO-DOCUMENTATION-INDEX.md`; it defines the
demo authority, runbook sequence, generated-artifact boundary, and exclusions.

## Business authority

- `REQUIREMENTS-V2.md` — approved production rules and role boundaries.
- `PRODUCT-SPEC.md` — product behavior and workflow acceptance.
- `USER-FLOWS.md` — step-by-step role workflows.
- `DATA-MODEL.md` — records, relationships, and state rules.
- `UX-PHILIPPINE-CONTROLS.md` — currency, language, privacy, and PH controls.
- `DESIGN-SYSTEM.md` — visual tokens, responsive behavior, accessibility, and
  the production-to-demo design-change protocol.
- `UI-UX-ISSUES-2026-08-09.md` — current demo findings and production
  carry-forward fixes for menus, grids, and responsive forms.
- `REPOSITORY-BACKUP-RUNBOOK.md` — public GitHub synchronization, encrypted mirror,
  restore checks, and exposure response.
- `POST-CHANGE-SYNC-CHECKLIST.md` — required research, documentation sync,
  validation, signed commit, HTTPS publication, and remote verification flow.

## Security and operations

- `PRODUCTION-VPS-DEPLOYMENT.md` — production VPS, secrets, Quadlets, backups,
  and Caddy activation. This is operator-only material.
- `PRODUCTION-BACKUP-RESTORE-RUNBOOK.md` — owner-only CLI dry-run restore,
  encrypted backup catalog, retention, and recovery evidence.
- `PRODUCTION-INCIDENT-RECOVERY-PODMAN-RM.md` — safe recovery after broad
  rootless Podman container removal, with bind-mount and secret checks.
- `PASSWORD-RECOVERY.md` — activation and self-service recovery controls.
- `DATA-EXPORTS.md` — CSV/full archive behavior and retention.
- `SUPPORT-TICKETS.md` — user support tickets, Admin replies, and notifications.
- `INCIDENT-REPORTING.md` — reporting and response expectations.
- `QUALITY-ASSURANCE.md` — source and deployed acceptance evidence.
- `PHASE-0-REVIEW.md` — sign-off checklist; unchecked items require evidence.

## Handoff

- `HANDOFF-BRIDGE-PIMASCOR.md` — boundary, ownership, access transfer,
  acceptance, and source/IP terms.
- `../handoff/bridge-pimascor/README.md` — handoff packet navigation and the
  authoritative production account list.
- `../handoff/bridge-pimascor/BRIDGE-TEAM-MESSAGE.md` — approved message for
  notifying Bridge Team about the official client handoff.
- `../handoff/bridge-pimascor/client-packet/` — current client-facing PDF and
  delivery manifest. The official deliverable is
  `00-pimascor-production-handoff-guide.pdf`.

## Infrastructure ownership

- `../infra/scripts/` — deployment and maintenance commands.
- `../infra/quadlet/production/` — production-only rootless Podman units.
- `../infra/caddy/` — production Caddy fragments and reviewed configuration.
- `DEMO-HOSTING-DECISION-2026-09-24.md` and `../infra/docker-compose/` —
  current OrbStack demo only; do not mix with production paths or secrets.
  Older demo Quadlets and VPS runbook are historical deployment material.

The Mac-side production release builder is
`../infra/scripts/build-local-release.sh`; the transfer entry point is
`../infra/scripts/deploy-production-vps.sh`. The transfer script builds inside
the Docker Sandbox and sends the source plus commit-matched API/web artifacts.
The VPS updater only activates the supplied bundle. The optional
`--refresh-account-manifest` flag is the only path that intentionally replaces
the account-bootstrap secret; ordinary releases preserve it.

## Change-control rules

1. Confirm the change belongs to production before editing.
2. Update the authoritative Markdown document and the implementation together.
3. Run focused tests, then the full QA gate when practical.
4. Never commit credentials, Podman secret values, live data, or reset tokens.
5. Record the accepted commit in the handoff manifest.
6. Use signed commits and GitHub CLI remote checks over the configured HTTPS
   remote; verify the GitHub signature rather than assuming a local commit is
   verified.
7. After every update, revision, or modification, follow
   `POST-CHANGE-SYNC-CHECKLIST.md` and record any remaining unrelated worktree
   changes without staging them.

Local Git `main` is the production documentation source of truth. GitHub
`origin/main` is synchronized after local validation and signed commit
creation; a remote SHA mismatch means the mirror is stale.

## Repository hygiene

The public portfolio repository contains existing history, including earlier
reference and client-facing material. New commits must contain only reviewed
public-safe files under `REPOSITORY-EXPOSURE-AND-NDA.md`. Credentials, private
keys, local databases, secrets, and runtime data remain excluded. The root
`.gitignore` is one prevention layer; staged-path review is still required.
