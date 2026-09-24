# PIMASCOR demo documentation index

This is the starting point for any agent, operator, reviewer, or maintainer
working on the synthetic demo only. It follows the Diátaxis separation of
tutorials, how-to guides, reference material, and explanations. Production
instructions remain separate and must not be inferred from this index.

Start with [the consistency remediation plan](CONSISTENCY-REMEDIATION-PLAN.md)
for the phased review and maintenance workflow.

All demo changes are committed with local `git`, then published to the private
GitHub HTTPS remote using `gh`. VPS transfer/activation SSH is a separate
deployment operation.

## Authority and scope

Before changing or publishing demo content, read
`REPOSITORY-EXPOSURE-AND-NDA.md`. It defines which source and documentation
may enter the private GitHub mirror and which client material must stay local.

`UI-UX-ISSUES-2026-08-09.md` is the current demo UI issue and production
carry-forward record. Use its interaction and responsive rules instead of
inferring behavior from screenshots.

1. `DEMO-BUILD-SOURCE-OF-TRUTH-2026-08-08.md` is the controlling demo
   decision record. Newer dated demo decisions supersede it.
2. `../infra/docker-compose/README.md` is the current macOS OrbStack demo
   runbook. It covers the manual Docker Sandbox image build, image export and
   load, Compose startup, explicit migration/seed/reset, tunnel route, CDN
   behavior, and rollback. `DEMO-VPS-DEPLOYMENT.md` is superseded historical
   VPS guidance and must not be used for this demo.
3. Code, Quadlets, and scripts are the implementation evidence. Documentation
   must not claim a deployed result without recorded local or VPS evidence.
4. `docs/reference/` contains quotation-format reference files. They inform
   dynamic rendering; they are not static application data.

## Tutorial — first macOS demo run

- Read this file and the source-of-truth decision record.
- Read `FACTUAL-BASIS.md` before treating any local, VPS, or external state as
  verified evidence.
- Follow `../infra/docker-compose/README.md` one command at a time.
- Build and export the image with `jk-sbx-project`, then load it into OrbStack.
- Run migration, account initialization, and demo reset as separate manual
  commands before starting the API.
- Complete the health, Admin entry, role-workspace, and quotation-preview
  checks at `https://pimascor.delegateops.business`.

## How-to guides — operational tasks

- `../infra/docker-compose/README.md` — manual macOS Sandbox build, OrbStack
  Compose startup, Cloudflare Tunnel route, CDN behavior, and rollback.
- `DEMO-VPS-DEPLOYMENT.md` — superseded VPS runbook retained for historical
  context; it is not an authority for the macOS demo.
- `DEMO-INCIDENT-RECOVERY-PODMAN-RM.md` — recovery after broad rootless Podman
  stop/remove commands; inspect first and preserve demo data.
- `../infra/scripts/deploy-demo-vps.sh` — Mac-side transfer entry point.
- `../infra/scripts/build-local-release.sh` — optional local Docker Sandbox
  builder for a manually inspected demo release bundle.
- `../infra/scripts/update-demo.sh` — VPS-only guarded artifact activation,
  migration, and demo reset.
- `../infra/scripts/reconcile-demo-web-root.sh` — Caddy mount and stale-stage
  reconciliation; it validates canonical paths so `/home/jk` and
  `/var/home/jk` equivalents are not falsely rejected.
- `QUALITY-ASSURANCE.md` — source and deployed acceptance evidence.
- `GIT-WORKFLOW.md` — local commit, private GitHub CLI push, and SHA checks.

## Reference — implementation contracts

- `DEMO-BUILD-SOURCE-OF-TRUTH-2026-08-08.md` — one-click demo entry, role evaluation,
  exports, document viewer, GM override, and precedence rules.
- `REQUIREMENTS-V2.md`, `PRODUCT-SPEC.md`, `USER-FLOWS.md` — general workflow
  contracts; apply the newer demo overrides first.
- `DATA-EXPORTS.md` — CSV and full-archive behavior; full archives stay
  disabled in demo.
- `SUPPORT-TICKETS.md` — shared production ticket workflow and demo simulation.
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

The demo role switch intentionally has one canonical location in Admin
Controls. Do not re-add a duplicate top-bar selector in production; carry the
same single-surface pattern forward while preserving the preview banner and
return action.

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
