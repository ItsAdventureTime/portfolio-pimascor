# PIMASCOR production documentation map

This index is the starting point for any agent, operator, reviewer, or future
maintainer working on production. Demo documentation is intentionally separate
and must not be used as a production deployment instruction.

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
- `REPOSITORY-BACKUP-RUNBOOK.md` — private GitHub continuity, encrypted mirror,
  restore checks, and exposure response.

## Security and operations

- `PRODUCTION-VPS-DEPLOYMENT.md` — production VPS, secrets, Quadlets, backups,
  and Caddy activation. This is operator-only material.
- `PRODUCTION-BACKUP-RESTORE-RUNBOOK.md` — owner-only CLI dry-run restore,
  encrypted backup catalog, retention, and recovery evidence.
- `PASSWORD-RECOVERY.md` — activation and self-service recovery controls.
- `DATA-EXPORTS.md` — CSV/full archive behavior and retention.
- `INCIDENT-REPORTING.md` — reporting and response expectations.
- `QUALITY-ASSURANCE.md` — source and deployed acceptance evidence.
- `PHASE-0-REVIEW.md` — sign-off checklist; unchecked items require evidence.

## Handoff

- `HANDOFF-BRIDGE-PIMASCOR.md` — boundary, ownership, access transfer,
  acceptance, and source/IP terms.
- `../handoff/bridge-pimascor/README.md` — handoff packet navigation and the
  authoritative production account list.
- `../handoff/bridge-pimascor/client-packet/` — client-facing PDFs and manifest.
  Regenerate PDFs after source-document revisions before delivery.

## Infrastructure ownership

- `../infra/scripts/` — deployment and maintenance commands.
- `../infra/quadlet/production/` — production-only rootless Podman units.
- `../infra/caddy/` — production Caddy fragments and reviewed configuration.
- `../infra/quadlet/demo/` and `DEMO-VPS-DEPLOYMENT.md` — demo only; do not
  mix with production paths or secrets.

The Mac-side production transfer entry point is
`../infra/scripts/deploy-production-vps.sh`. The optional
`--refresh-account-manifest` flag is the only path that intentionally replaces
the account-bootstrap secret; ordinary releases preserve it.

## Change-control rules

1. Confirm the change belongs to production before editing.
2. Update the authoritative Markdown document and the implementation together.
3. Run focused tests, then the full QA gate when practical.
4. Never commit credentials, Podman secret values, live data, or reset tokens.
5. Record the accepted commit in the handoff manifest.
6. Use signed commits and GitHub CLI remote checks; verify the GitHub signature
   rather than assuming a local commit is verified.

Local Git `main` is the production documentation source of truth. GitHub
`origin/main` is synchronized after local validation and signed commit
creation; a remote SHA mismatch means the mirror is stale.

## Repository hygiene

The remote repository contains source, migrations, tests, reviewed
documentation, deployment definitions, approved reference PDFs, client-facing
handoff material, and authorized project records for this private mirror. It
excludes credentials, private keys, local databases, secrets, and runtime data.
The root `.gitignore` is the prevention layer for those always-excluded files.
