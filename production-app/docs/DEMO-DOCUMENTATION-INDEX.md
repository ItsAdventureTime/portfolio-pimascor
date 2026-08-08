# PIMASCOR demo documentation index

This is the starting point for any agent, operator, reviewer, or maintainer
working on the synthetic demo only. It follows the Diátaxis separation of
tutorials, how-to guides, reference material, and explanations. Production
instructions remain separate and must not be inferred from this index.

## Authority and scope

1. `DEMO-BUILD-SOURCE-OF-TRUTH-2026-08-08.md` is the controlling demo
   decision record. Newer dated demo decisions supersede it.
2. `DEMO-VPS-DEPLOYMENT.md` is the current demo release runbook and contains
   the approved Mac-to-VPS transfer and VPS activation sequence. `infra/README.md`
   remains a lower-level manual/bootstrap reference.
3. Code, Quadlets, and scripts are the implementation evidence. Documentation
   must not claim a deployed result without recorded local or VPS evidence.
4. `docs/reference/` contains quotation-format reference files. They inform
   dynamic rendering; they are not static application data.

## Tutorial — first demo release

- Read this file and the source-of-truth decision record.
- Read `FACTUAL-BASIS.md` before treating any local, VPS, or external state as
  verified evidence.
- Run the local transfer command in `DEMO-VPS-DEPLOYMENT.md`.
- Run the VPS activation command in that same runbook.
- Complete the health, Admin entry, role-workspace, quotation-preview,
  protected-document, and cache-validation checks before CDN purge.

## How-to guides — operational tasks

- `DEMO-VPS-DEPLOYMENT.md` — transfer, activate, validate, rollback, cleanup,
  and targeted Bunny cache purge.
- `../infra/scripts/deploy-demo-vps.sh` — Mac-side transfer entry point.
- `../infra/scripts/update-demo.sh` — VPS-only guarded build/migration/reset.
- `../infra/scripts/reconcile-demo-web-root.sh` — Caddy mount and stale-stage
  reconciliation; it validates canonical paths so `/home/jk` and
  `/var/home/jk` equivalents are not falsely rejected.
- `../infra/scripts/cleanup-demo-rollback.sh` — remove obsolete rollback
  directories only after the active release is verified.
- `QUALITY-ASSURANCE.md` — source and deployed acceptance evidence.
- `GIT-WORKFLOW.md` — local commit, private GitHub CLI push, and SHA checks.

## Reference — implementation contracts

- `DEMO-BUILD-SOURCE-OF-TRUTH-2026-08-08.md` — demo entry, role evaluation,
  exports, document viewer, GM override, and precedence rules.
- `REQUIREMENTS-V2.md`, `PRODUCT-SPEC.md`, `USER-FLOWS.md` — general workflow
  contracts; apply the newer demo overrides first.
- `DATA-EXPORTS.md` — CSV and full-archive behavior; full archives stay
  disabled in demo.
- `API-CONTRACT.md` and `DATA-MODEL.md` — API/state boundaries.
- `../apps/api/README.md` and `../apps/web/README.md` — service-specific
  build, reset, and local-development references.
- `../infra/quadlet/demo/` and `../infra/caddy/bridge-ph-pimascor-demo.Caddyfile`
  — demo runtime definitions and public routing.

## Explanation and evidence policy

- `FACTUAL-BASIS.md` — distinguishes repository, VPS, and external evidence.
- `INCIDENT-REPORTING.md` — incident handling and non-disclosure rules.
- `DESIGN-SYSTEM.md`, `UX-PHILIPPINE-CONTROLS.md`, and `PWA-INSTALLATION.md`
  — user-experience and accessibility context.

## Generated and non-authoritative material

`../handoff/bridge-pimascor/client-packet/` contains generated PDF snapshots
from a prior handoff. They are delivery artifacts, not the source of truth;
regenerate them from current Markdown before issuing a new packet. The
production handoff README explicitly separates that packet from demo runtime
instructions.

Do not use these production-only files for a demo deployment:

- `PRODUCTION-VPS-DEPLOYMENT.md`
- `../infra/quadlet/production/`
- `../infra/scripts/update-production.sh`
- production Caddy fragments and production secrets

## Change checklist

When demo behavior changes, update the implementation, this index, the source
of truth, and the affected runbook together. Run the documented checks, record
the exact commit, commit locally, push through GitHub CLI to the private
remote, and verify local and remote SHAs match. Never commit credentials,
tokens, live data, or generated machine metadata.
