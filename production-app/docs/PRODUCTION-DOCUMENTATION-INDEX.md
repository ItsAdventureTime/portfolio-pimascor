# PIMASCOR production documentation map

This index is the starting point for any agent, operator, reviewer, or future
maintainer working on production. Demo documentation is intentionally separate
and must not be used as a production deployment instruction.

## Business authority

- `REQUIREMENTS-V2.md` — approved production rules and role boundaries.
- `PRODUCT-SPEC.md` — product behavior and workflow acceptance.
- `USER-FLOWS.md` — step-by-step role workflows.
- `DATA-MODEL.md` — records, relationships, and state rules.
- `UX-PHILIPPINE-CONTROLS.md` — currency, language, privacy, and PH controls.

## Security and operations

- `PRODUCTION-VPS-DEPLOYMENT.md` — production VPS, secrets, Quadlets, backups,
  and Caddy activation. This is operator-only material.
- `PASSWORD-RECOVERY.md` — activation and self-service recovery controls.
- `DATA-EXPORTS.md` — CSV/full archive behavior and retention.
- `INCIDENT-REPORTING.md` — reporting and response expectations.
- `QUALITY-ASSURANCE.md` — source and deployed acceptance evidence.
- `PHASE-0-REVIEW.md` — sign-off checklist; unchecked items require evidence.

## Handoff

- `docs/HANDOFF-BRIDGE-PIMASCOR.md` — boundary, ownership, access transfer,
  acceptance, and source/IP terms.
- `handoff/bridge-pimascor/README.md` — handoff packet navigation and the
  authoritative production account list.
- `handoff/bridge-pimascor/client-packet/` — client-facing PDFs and manifest.
  Regenerate PDFs after source-document revisions before delivery.

## Infrastructure ownership

- `infra/scripts/` — deployment and maintenance commands.
- `infra/quadlet/production/` — production-only rootless Podman units.
- `infra/caddy/` — production Caddy fragments and reviewed configuration.
- `infra/quadlet/demo/` and `docs/DEMO-VPS-DEPLOYMENT.md` — demo only; do not
  mix with production paths or secrets.

## Change-control rules

1. Confirm the change belongs to production before editing.
2. Update the authoritative Markdown document and the implementation together.
3. Run focused tests, then the full QA gate when practical.
4. Never commit credentials, Podman secret values, live data, or reset tokens.
5. Record the accepted commit in the handoff manifest.
6. Use signed commits and GitHub CLI remote checks; verify the GitHub signature
   rather than assuming a local commit is verified.
