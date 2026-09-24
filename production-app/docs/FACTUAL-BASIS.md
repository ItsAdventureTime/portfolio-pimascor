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

## Historical VPS layout (superseded for the demo)

**Confirmed by owner on 30 July 2026.** These were the only application and
Quadlet paths allowed for the earlier VPS demo deployment:

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

## Historical VPS deployment evidence boundary

**Confirmed in the repository's earlier VPS setup.** The demo transfer helper
stages source under `~/bridge-ph/pimascor-demo/source`; the demo updater and demo Quadlets
use `~/bridge-ph/pimascor-demo` for runtime data; the compiled demo PWA is written to
`~/bridge-ph/pimascor-demo/web-dist`; production backup Quadlets use
`~/bridge-ph/pimascor`.

This confirms intended repository configuration only. It does not establish
that the VPS has received the commit, that a migration completed, that a service
is healthy, or that a CDN purge occurred. Those facts require current VPS or
provider command output.

## Git synchronization boundary

**Confirmed by owner on 2026-09-24.** The selected demo GitHub target is the
public HTTPS repository
`https://github.com/ItsAdventureTime/portfolio-pimascor.git`. At planning time,
the local `origin` still pointed to `bridge-pimascor`; both endpoints reported
the same `main` SHA and public visibility. The publisher must verify the
current remote URL and SHA before pushing. A successful push proves GitHub
synchronization only; it does not prove Mac, Tunnel, or VPS deployment.

## Required demo deployment handoff

**Confirmed by owner on 2026-09-24.** The current demo target is the Mac mini
M1 with OrbStack and the existing Cloudflare Tunnel at
`https://pimascor.delegateops.business`. Follow
`DEMO-HOSTING-DECISION-2026-09-24.md` and
`../infra/docker-compose/README.md`. The older VPS transfer/activation
instructions remain repository history but are not the current demo deployment
path. A Docker Sandbox build proves only the image build. OrbStack command
output proves local container startup. An external HTTPS check proves only the
tested public route and time. Record each separately; no current runtime
state has been verified by this planning document.

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
