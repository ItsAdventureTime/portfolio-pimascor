# Production incident recovery: rootless Podman containers removed

This runbook applies when a broad command such as `podman stop -a` followed by
`podman rm -a` removes the rootless user's containers. It does not assume that
production data was deleted.

## What the command changes

`podman stop -a` stops all running containers visible to the current rootless
user. `podman rm -a` removes those container objects; it does not remove images
and does not remove named volumes unless a separate volume-removal option or
prune command is used. Production PostgreSQL and uploads are bind-mounted under
`~/bridge-ph/pimascor`, so their survival must be checked directly.

The command's `rm -rf /home/jk/bridge-ph/accustandard-demo/` affects only that
explicit path. It is unrelated to the production source and data paths used by
PIMASCOR. Do not run another broad `podman rm`, `podman volume prune`, or
recursive deletion command during recovery.

## 1. Freeze destructive changes and inventory the VPS

Log in as the rootless VPS user `jk`. Run this read-only inventory first:

```bash
ssh -p 22 jk@216.75.75.136 'set -eu; printf "== user ==\n"; id; printf "== production paths ==\n"; for p in /var/home/jk/bridge-ph/pimascor /var/home/jk/bridge-ph/pimascor/source /var/home/jk/bridge-ph/pimascor/data/postgres/18/docker /var/home/jk/bridge-ph/pimascor/data/uploads /var/home/jk/pimascor /var/home/jk/pimascor-demo; do if [ -e "$p" ]; then stat -c "%F %U:%G %a %n" "$p"; else printf "MISSING %s\n" "$p"; fi; done; printf "== containers ==\n"; podman ps -a --no-trunc; printf "== images ==\n"; podman images --format "{{.Repository}}:{{.Tag}} {{.ID}}"; printf "== volumes ==\n"; podman volume ls; printf "== production secrets ==\n"; for s in bridge_ph_pimascor_postgres_password bridge_ph_pimascor_database_url bridge_ph_pimascor_resend_api_key bridge_ph_pimascor_b2_key_id bridge_ph_pimascor_b2_application_key bridge_ph_pimascor_pgpass bridge_ph_pimascor_restic_password bridge_ph_pimascor_account_bootstrap; do podman secret exists "$s" && printf "present %s\n" "$s" || printf "missing %s\n" "$s"; done; printf "== user units ==\n"; systemctl --user list-unit-files "bridge-ph-pimascor-*" "caddy.service" --no-legend'
```

Do not paste secret values, database contents, or backup credentials into an
incident report. The inventory records existence and metadata only.

## 2. Re-deploy the committed production source

### Interpreting the reported inventory

The observed state in this incident is consistent with container removal, not
database deletion:

- `/var/home/jk/bridge-ph/pimascor`, its source, and its PostgreSQL bind path
  are present.
- `bridge-ph-pimascor-db` is running and healthy.
- The production API, account bootstrap, export worker, dump, and backup
  containers are absent because their container objects were removed; their
  generated Quadlet services remain available to recreate them.
- `caddy` is running again because its user-level service recreated it.
- `stat` may show `UNKNOWN` for the PostgreSQL directory owner when the
  container's numeric PostgreSQL UID has no matching host `/etc/passwd` entry.
  That output alone is not evidence of corruption; inspect the container
  health and mount rather than changing ownership speculatively.

The `linkwarden-*`, demo, and other site containers shown by `podman ps` are
separate workloads. Do not remove or reset them while recovering PIMASCOR.

If the production source directory is missing or incomplete, run this on the
Mac. The transfer contains committed source and Quadlet definitions only; it
does not transfer secrets, PostgreSQL data, uploads, or backups:

```bash
/Users/jk.deguzman/dev/bridge-ph_Dashboard/production-app/infra/scripts/deploy-production-vps.sh
```

The script replaces only `/var/home/jk/bridge-ph/pimascor/source`. It does not
replace `/var/home/jk/bridge-ph/pimascor/data`, `backup-staging`,
`backup-catalog`, `restic-cache`, or the Podman secret store.

## 3. Recreate containers from Quadlets

If the PostgreSQL bind-mounted data directory exists and the required secrets
are present, run on the VPS as `jk`:

```bash
cd /var/home/jk/bridge-ph/pimascor/source && ./infra/scripts/update-production.sh --source /var/home/jk/bridge-ph/pimascor/source
```

`update-production.sh` reinstalls the production Quadlets, regenerates the
user-level services, recreates missing containers, rebuilds the API and web
images, runs recorded migrations, and restarts the production workers. It does
not reset the database or seed fictional records. If the API fails to start,
the updater now prints the user-unit status, recent user journal, and recent
API container log automatically, without printing secret contents. Preserve
that diagnostic output for the incident record; do not repeatedly restart the
service while investigating the first failure.

If any production secret is reported missing, stop and run the interactive
provisioner as `jk`; never put a secret in a command argument or source file:

```bash
cd /var/home/jk/bridge-ph/pimascor/source && ./infra/scripts/provision-production-secrets.sh
```

## 4. If PostgreSQL data is missing

Do not run the updater against an empty production data path until recovery is
planned; doing so can initialize a new empty database and obscure the incident.
Use the encrypted Backblaze B2 Restic repository as the recovery source:

```bash
cd /var/home/jk/bridge-ph/pimascor/source && ./infra/scripts/production-restore.sh --list
cd /var/home/jk/bridge-ph/pimascor/source && ./infra/scripts/production-restore.sh --snapshot latest --dry-run
cd /var/home/jk/bridge-ph/pimascor/source && ./infra/scripts/production-restore.sh --snapshot SNAPSHOT_ID --target /var/home/jk/bridge-ph/pimascor/restore-quarantine --execute
```

The restore helper refuses the live production root. Inspect the quarantine
database dump, migration head, uploads, checksums, and backup catalog before a
separate owner-approved cutover. There is no web restore operation.

## 5. Restore the shared rootless Caddy service

After the production services are healthy, activate the shared rootless Caddy
Quadlet as `jk`:

```bash
cd /var/home/jk/bridge-ph/pimascor/source && ./infra/scripts/install-production-caddy.sh
systemctl --user status --no-pager caddy.service
curl --fail --location https://delegateops.business/pimascor/api/v1/health
```

The installer formats and validates the Caddyfile in disposable containers,
preflights every shared bind-mount source, reloads the user Quadlet generator,
and restarts `caddy.service`. It does not use a root-level system service.

## Recovery evidence

Record the incident time, inventory result, deployed commit, service statuses,
health-check result, selected backup snapshot, quarantine checksum results, and
owner approval. Never record Podman secret contents, Restic passwords, B2 keys,
session cookies, or reset tokens.
