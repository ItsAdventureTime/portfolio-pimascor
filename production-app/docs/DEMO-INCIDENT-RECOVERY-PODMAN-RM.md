# Demo incident recovery: broad rootless Podman removal

## Recovery status

On 2026-08-10, the owner reported that the demo recovery completed
successfully. This is owner-reported evidence; retain the service health and
role-walkthrough output separately as deployment evidence.

This runbook applies after a command such as:

```bash
podman stop -a
podman rm -a
```

Those flags target every container visible to the current rootless user. They
stop and remove container objects, but do not remove images, named volumes, or
bind-mounted application data by themselves. The separate `rm -rf` command
affects only the exact directory named in that command. Do not run another
broad Podman removal, prune, or recursive deletion command during recovery.

## Canonical demo paths

- Application source, data, and web assets:
  `/var/home/jk/bridge-ph/pimascor-demo`
- Transferred source:
  `/var/home/jk/bridge-ph/pimascor-demo/source`
- PostgreSQL data:
  `/var/home/jk/bridge-ph/pimascor-demo/data/postgres/18/docker`
- Caddy-served web root:
  `/var/home/jk/bridge-ph/pimascor-demo/web-dist`
- Demo Quadlets:
  `/var/home/jk/.config/containers/systemd/bridge-ph/pimascor-demo`

The invalid legacy path `~/pimascor-demo` must not be used.

## 1. Read-only inventory on the VPS

After logging in as `jk`, run this first. It records metadata only and does not
change containers, files, networks, volumes, or secrets:

```bash
printf '== paths ==\n'; for p in /var/home/jk/bridge-ph/pimascor-demo /var/home/jk/bridge-ph/pimascor-demo/source /var/home/jk/bridge-ph/pimascor-demo/data/postgres/18/docker /var/home/jk/bridge-ph/pimascor-demo/web-dist /var/home/jk/.config/containers/systemd/bridge-ph/pimascor-demo; do if [ -e "$p" ]; then stat -c '%F %U:%G %a %n' "$p"; else printf 'MISSING %s\n' "$p"; fi; done; printf '== containers ==\n'; podman ps -a --no-trunc; printf '== images ==\n'; podman images --format '{{.Repository}}:{{.Tag}} {{.ID}}'; printf '== demo secrets ==\n'; for s in bridge_ph_pimascor_demo_postgres_password bridge_ph_pimascor_demo_database_url bridge_ph_pimascor_demo_resend_api_key bridge_ph_pimascor_demo_b2_key_id bridge_ph_pimascor_demo_b2_application_key; do podman secret exists "$s" && printf 'present %s\n' "$s" || printf 'missing %s\n' "$s"; done; printf '== user units ==\n'; systemctl --user list-unit-files 'bridge-ph-pimascor-demo-*' 'caddy.service' --no-legend
```

Do not paste secret values, database contents, or tokens into a report.

## 2. Recreate the demo from the committed source

If the source directory exists and the PostgreSQL data directory exists, run
this on the VPS as `jk` to reinstall Quadlets and recreate removed containers
without resetting synthetic records:

```bash
cd ~/bridge-ph/pimascor-demo/source && ./infra/scripts/update-demo.sh --source ~/bridge-ph/pimascor-demo/source --api-image-archive ~/bridge-ph/pimascor-demo/release-artifacts/COMMIT/api-image.tar --web-dist ~/bridge-ph/pimascor-demo/release-artifacts/COMMIT/web-dist --keep-demo-data && bash ./infra/scripts/reconcile-demo-web-root.sh
```

The updater recreates the demo database/API containers from Quadlets and
restarts the shared Caddy service. Keep the rollback material it reports until
health and role walkthroughs pass.

If the source directory is missing, run the Mac transfer command from
`DEMO-VPS-DEPLOYMENT.md`, then repeat the VPS command above. The transfer does
not replace demo data or Podman secrets.

If the PostgreSQL data directory is missing, stop before running the updater
with `--keep-demo-data`; first determine whether a VPS snapshot or approved
backup exists. Do not initialize a new database while treating the incident as
recovered.

## 3. Verify before CDN purge

```bash
systemctl --user is-active bridge-ph-pimascor-demo-db.service
systemctl --user is-active bridge-ph-pimascor-demo-api.service
systemctl --user is-active caddy.service
curl --fail --show-error https://delegateops.business/pimascor/demo/api/v1/health
```

Then complete the demo QA walkthrough and only afterward perform the targeted
Bunny purge. A successful container restart is not proof that the public route
serves the new release.

## Prevention

Never use `podman stop -a`, `podman rm -a`, `podman system prune`, or recursive
deletion against a shared VPS account. Operate the named Quadlet unit only and
take a read-only inventory before any cleanup.
