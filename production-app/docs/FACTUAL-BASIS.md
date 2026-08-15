# Factual basis and evidence policy

For demo-only behavior, the newest source-of-truth overlay is
`DEMO-BUILD-SOURCE-OF-TRUTH-2026-08-08.md`. It supersedes older demo wording;
this evidence policy still governs what may be claimed as locally verified,
VPS-verified, or externally verified.

This document controls how PIMASCOR documentation, deployment instructions,
and implementation notes state facts. It prevents an observed file, a user
statement, a verified command result, and an assumption from being presented as
the same kind of evidence.

## Evidence labels

- **Confirmed by owner**: directly supplied by the system owner or operator.
- **Confirmed in repository**: present in the checked local source and named
  commit.
- **Confirmed by command output**: captured from the relevant host or service.
- **External reference**: supported by the linked primary documentation.
- **Inference**: a reasoned recommendation, not a verified fact.
- **Unknown**: requires a command, log, configuration file, or owner decision
  before an instruction may depend on it.

Never convert an inference or unknown into a command that can modify the VPS,
database, storage, secrets, DNS, or CDN. State the missing evidence and obtain
it first.

## Confirmed VPS layout

**Confirmed by owner on 30 July 2026.** These are the only application and
Quadlet paths that the current demo deployment instructions may use:

```text
~/bridge-ph/pimascor-demo
~/bridge-ph/pimascor
~/.config/containers/systemd/bridge-ph/pimascor
~/.config/containers/systemd/bridge-ph/pimascor-demo
```

Demo source, runtime data, and compiled web assets remain under
`~/bridge-ph/pimascor-demo`. Quadlets remain under
`~/.config/containers/systemd/bridge-ph/pimascor-demo`.

## Confirmed cleanup scope

**Confirmed by owner on 30 July 2026.** The only erroneous VPS directories
authorized for removal are:

```text
~/bridge-ph/pimascor-demo-release
~/bridge-ph/pimascor-demo-release.previous.20260729T161528Z
~/bridge-ph/releases
```

The repository provides a local SSH helper that targets only those paths:
`infra/scripts/cleanup-mistaken-demo-vps-paths.sh`. Its existence does **not**
prove that the deletion has run. Treat deletion as unknown until the operator
records the command output from the VPS.

## Current deployment evidence boundary

**Confirmed in the current local repository HEAD.** The demo transfer helper
stages source under `~/bridge-ph/pimascor-demo/source`; the demo updater and demo Quadlets
use `~/bridge-ph/pimascor-demo` for runtime data; the compiled demo PWA is written to
`~/bridge-ph/pimascor-demo/web-dist`; production backup Quadlets use
`~/bridge-ph/pimascor`.

This confirms intended repository configuration only. It does not establish
that the VPS has received the commit, that a migration completed, that a service
is healthy, or that a CDN purge occurred. Those facts require current VPS or
provider command output.

## Git synchronization boundary

**Confirmed in the local repository configuration.** The configured `origin` is
the private HTTPS GitHub repository
`https://github.com/ItsAdventureTime/bridge-pimascor.git`.
Every tracked change must be validated, committed locally, and pushed to that
private remote. A successful push proves GitHub synchronization only; it does
not prove VPS deployment.

## Required demo deployment handoff

**Confirmed by owner on 30 July 2026; deployment workflow revised on 16 August
2026.** Whenever a completed change affects the demo release, the handoff must
include the local transfer command and the commit-specific VPS activation
command below:

```bash
/Users/jk.deguzman/dev/bridge-ph_Dashboard/production-app/infra/scripts/deploy-demo-vps.sh
```

Run that command locally on the Mac. After it succeeds and after logging in,
run the exact activation command printed by the transfer script. Its shape is:

```bash
cd ~/bridge-ph/pimascor-demo/source && ./infra/scripts/update-demo.sh --source ~/bridge-ph/pimascor-demo/source --api-image-archive ~/bridge-ph/pimascor-demo/release-artifacts/COMMIT/api-image.tar --web-dist ~/bridge-ph/pimascor-demo/release-artifacts/COMMIT/web-dist && bash ./infra/scripts/reconcile-demo-web-root.sh
```

**Confirmed in repository.** The local transfer builds the API image and static
PWA in the Docker Sandbox, then sends the reviewed source and commit-matched
release artifacts; it excludes local `apps/web/dist`, `node_modules`, virtual
environments, and test data. A local check is evidence of local validation only.
The VPS updater loads the API image and stages the PWA before it activates the
demo. Report local and VPS evidence separately and never claim the VPS update,
migration, restart, health check, or CDN purge completed until its command
output is available.

## Sales quotation printing

**Confirmed in the current local repository.**
`docs/reference/AAA FORMAT QUOTATION.pdf` is a visual layout reference, not a
static form or a source of quotation values. The quotation preview and print
copy render the selected persisted `ApiQuotation`: its reference, client,
shipment details, terms, approval state, line items, currencies, amounts, and
per-currency totals. Placeholder amounts or client details must never be copied
from the reference PDF into a live quotation.

## Required wording for operational work

1. Cite the file path, command output, owner statement, or primary source near
   each operational claim.
2. Say "run this to verify" when a server state has not been observed.
3. Say "not yet verified" rather than claiming a deployment, deletion, restart,
   migration, backup, or purge completed.
4. Stop and ask for direction if a requested change needs an unknown path,
   credential, retention rule, legal requirement, or production decision.
5. Keep commands scoped to exact paths. Do not add backup, rollback, deletion,
   or external-service operations that the owner did not authorize.

## External references

- [Podman user Quadlet search paths](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html)
- [Bunny CDN cache purge documentation](https://docs.bunny.net/cdn/purge-cache)
