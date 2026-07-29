# Demo VPS release procedure

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

## Before starting

1. Keep the existing demo online until the new release has passed its health and
   browser checks. Do not purge Bunny yet.
2. Transfer the reviewed `production-app` source tree containing commit
   `0008c19` and this runbook to an approved release directory on the VPS. Use
   your approved private transfer method; this repository has no public remote.
3. Confirm that the release directory contains `apps/api/migrations/versions/20260729_0011_data_exports.py` and
   `infra/scripts/update-demo.sh`.
4. Sign in to the VPS as the same non-root account that owns the demo services.
   The update script refuses root and checks that Podman is rootless.

## Deploy on the VPS

Set the release path to the directory you transferred, then run the guarded
demo updater. The default behavior applies migrations and reloads the approved
synthetic demo baseline, which is the correct choice for a demo release.

```bash
cd /path/to/production-app
./infra/scripts/update-demo.sh --source "$(pwd)"
```

Do not add `--keep-demo-data` unless preserving the current synthetic demo data
is explicitly required. That option retains current demo records while applying
forward migrations; it is not appropriate when the approved baseline needs to
be restored.

The updater builds the API and PWA, saves local rollback material, installs the
reviewed Quadlets, runs the database forward migration through the API/reset
entrypoint, restarts Caddy, and probes both the health endpoint and public demo
route. Stop if it reports an error. Do not purge the CDN after a failed update.

## Verify before any Bunny purge

Run these from the VPS under the demo service account:

```bash
systemctl --user is-active bridge-ph-pimascor-demo-db.service
systemctl --user is-active bridge-ph-pimascor-demo-api.service
curl --fail --show-error https://delegateops.business/pimascor/demo/api/v1/health
grep -R --quiet --fixed-strings 'Module-specific accounting CSVs' "$HOME/bridge-ph/pimascor-demo/web-dist/assets"
```

Then use a private/incognito browser window to check the public demo:

1. Sign in with an approved demo account.
2. Open **Accounting Export** and confirm **Billing CSV** and **Collections CSV**
   are visible.
3. Confirm the local-record archive action explains that archives are disabled
   in the demo; it must not send an email or produce a download.
4. Check one quotation print preview and one protected document viewer.
5. Check at least one non-admin role to confirm its restricted navigation still
   works.

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
