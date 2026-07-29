# Demo VPS release procedure

Read [Factual basis and evidence policy](FACTUAL-BASIS.md) first. The paths in
this guide are confirmed by the owner; completion of a transfer, cleanup,
migration, restart, or Bunny purge remains unverified until its current command
output is captured.

This procedure is only for the public synthetic-data demo at
`https://delegateops.business/pimascor/demo/`. It is not a production-data
deployment and must be run by the rootless Linux user that owns the demo
Podman/Caddy services.

## What this release deploys

- The API image, including Alembic migration `20260729_0011`.
- The compiled demo PWA.
- The reviewed demo Quadlet definitions and reset timer.
- Accounting exports as separate **Billing CSV** and **Collections CSV**.
- The local-record archive UI in its intentionally non-operational demo mode.

The demo API explicitly sets `DATA_EXPORT_ENABLED=false`. Do **not** run
`python -m pimascor_api.export_worker` on the demo VPS and do not set this value
to `true`. The demo uses synthetic records, and it must not create all-records
archives, email download notices, or retain archive objects in B2. Ordinary demo
document viewing and the existing private document storage configuration are not
changed by this safeguard.

## Transfer from this Mac

The demo VPS uses these fixed locations:

```text
/var/home/jk/pimascor-demo                    demo application files, data, and source
/var/home/jk/.config/containers/systemd/bridge-ph/pimascor-demo
                                               demo Quadlet definitions
```

Before transferring, remove the three mistakenly created release directories.
Run this once from the local Mac; it connects through `gatewaysentry`, prompts
for the VPS password, and deletes only the three named directories with no
backup:

    /Users/jk.deguzman/dev/bridge-ph_Dashboard/production-app/infra/scripts/cleanup-mistaken-demo-vps-paths.sh

From the local Terminal, run this exact command. It uses the existing
`gatewaysentry` SSH alias and prompts once for its configured VPS password:

    /Users/jk.deguzman/dev/bridge-ph_Dashboard/production-app/infra/scripts/deploy-demo-vps.sh

It sends the current local source tree (excluding Git history, virtual
environments, build output, and local test data) to
`/var/home/jk/pimascor-demo/source`. It first extracts to a private staging
directory, then replaces only that source directory. It creates no previous
source snapshot and does not remove demo data or B2 objects. The transfer
strips macOS AppleDouble metadata and sidecar files before extraction, so Linux
containers never receive those binary metadata files as possible Python
migration candidates.

## Activate from the VPS

After the source transfer completes, log in:

    ssh gatewaysentry

Then run this exact VPS command:

    cd ~/pimascor-demo/source && ./infra/scripts/update-demo.sh --source ~/pimascor-demo/source

## Required handoff for every demo-relevant change

Every implementation handoff must repeat the two single-line commands above:
the local transfer command first, then the VPS activation command after login.
It must also state which local checks actually passed and what the VPS command
still needs to verify. This repository's current workflow validates source
locally, transfers source, and builds the API/PWA on the VPS. It does not
transfer a locally compiled artifact, so a local build must never be presented
as evidence that the VPS has been updated.

## What the transfer does before starting

1. Keep the existing demo online until the new release has passed its health and
   browser checks. Do not purge Bunny yet.
2. It transfers the reviewed source tree and this
   runbook through the private SSH connection. This repository has no public
   remote.
3. The VPS updater confirms that migration `20260729_0011` and its required demo
   safeguards are present.
4. The remote update runs as the same non-root account selected by
   `gatewaysentry`; the update script refuses root and checks that Podman is
   rootless.

## Deployment behavior on the VPS

The VPS command above runs the guarded demo updater. Its default behavior
applies migrations and reloads the approved synthetic demo
baseline, which is the correct choice for a demo release. It builds the API and
PWA, saves local rollback material, installs the
reviewed Quadlets, runs the database forward migration through the API/reset
entrypoint, restarts Caddy, and probes both the health endpoint and public demo
route. Stop if it reports an error. Do not purge the CDN after a failed update.
Do not run `update-demo.sh` directly from macOS; it is intentionally VPS-only.

## Verify before any Bunny purge

Run these from the VPS under the demo service account:

```bash
systemctl --user is-active bridge-ph-pimascor-demo-db.service
systemctl --user is-active bridge-ph-pimascor-demo-api.service
curl --fail --show-error https://delegateops.business/pimascor/demo/api/v1/health
grep -R --quiet --fixed-strings 'Module-specific accounting CSVs' "$HOME/pimascor-demo/web-dist/assets"
```

Then use a private/incognito browser window to check the public demo:

1. Sign in with an approved demo account.
2. Open **Accounting Export** and confirm **Billing CSV** and **Collections CSV**
   are visible.
3. Confirm the local-record archive action explains that archives are disabled
   in the demo; it must not send an email or produce a download.
4. Check one quotation print preview and one protected document viewer.
5. Complete the five-role, responsive, and browser-engine checks in
   [Quality assurance release acceptance](QUALITY-ASSURANCE.md). Record the
   account, browser engine, viewport, and result for each check. A role-preview
   screen is not evidence that the server-side role gate accepts or rejects an
   action correctly.

If any check fails, use the rollback image/directory printed by the updater and
review the relevant `journalctl --user -u bridge-ph-pimascor-demo-api.service`
logs. Keep rollback material until the walkthrough is complete.

## Bunny CDN purge, only after verification

Prefer targeted URL purges. The demo API is explicitly `no-store`, and hashed
assets are immutable; normally only the mutable entry files need invalidation.
In Bunny's dashboard, or through an approved API key kept outside this project,
purge these exact URLs:

```text
https://delegateops.business/pimascor/demo/
https://delegateops.business/pimascor/demo/index.html
https://delegateops.business/pimascor/demo/sw.js
https://delegateops.business/pimascor/demo/manifest.webmanifest
```

Do not perform a full Pull Zone purge unless this Pull Zone serves only this demo
or a targeted purge is demonstrably insufficient. A full purge can temporarily
increase origin load and affect unrelated paths. If Bunny Perma-Cache is enabled,
remember that a full Pull Zone purge switches to a new cache directory rather
than deleting the old Perma-Cache files.

After the targeted purge, repeat the incognito walkthrough. If a browser still
uses an earlier service worker, close all demo tabs, reopen the demo, and reload
once; do not delete CDN or B2 objects as a cache workaround.

## References

- [Bunny CDN cache purge](https://docs.bunny.net/cdn/purge-cache)
- [Bunny exact URL purge API](https://docs.bunny.net/api-reference/core/purge/purge-url)
- [Podman Quadlet basic usage](https://docs.podman.io/en/latest/markdown/podman-quadlet-basic-usage.7.html)
- [Podman user Quadlet search paths](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html)
