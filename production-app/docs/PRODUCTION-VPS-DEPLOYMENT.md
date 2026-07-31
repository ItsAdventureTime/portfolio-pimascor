# PIMASCOR production deployment

This is the isolated production track. It does not use the demo runtime, demo
database, demo object prefix, demo containers, or demo web root.

Runtime paths:

- `~/bridge-ph/pimascor`: production source, web assets, PostgreSQL data,
  upload spool, backup staging, and restic cache.
- `~/.config/containers/systemd/bridge-ph/pimascor`: production Quadlets.
- Caddy serves `~/bridge-ph/pimascor/web-dist` at
  `https://delegateops.business/pimascor/`.

The production API uses `DEPLOYMENT_TIER=production`,
`APP_ENV=production`, private B2 storage, HTTPS-only cookies, Resend email,
and the durable export worker. It never runs `demo_reset` and does not seed
fictional clients or transactions.

## Production roles

The production policy from Section 1 of the owner correction document is:

| Role | Production authority |
| --- | --- |
| Admin | Full administration and attributable superuser access. |
| GM | Operational superuser except Administrator-only controls; approves and can release DCS Payment. |
| DCS | Executes DCS Payment and can override GM-owned approvals with an attributable reason. |
| Mich | Bookkeeper/reviewer; prepares accounting work, reviews/close Liquidations, and can export authorized records. |
| Requester | Creates and submits assigned operational requests; no management profitability, export, or payment authority. |

The GM/DCS escalation policy is enabled only when `DEPLOYMENT_TIER=production`;
the demo keeps its existing role policy.

## One-time VPS secrets

Create these as rootless Podman secrets while logged in as `jk`; use a secure
secret manager or an interactive prompt, never source-controlled files:

```text
bridge_ph_pimascor_postgres_password
bridge_ph_pimascor_database_url
bridge_ph_pimascor_resend_api_key
bridge_ph_pimascor_b2_key_id
bridge_ph_pimascor_b2_application_key
bridge_ph_pimascor_pgpass
bridge_ph_pimascor_restic_password
```

The database URL must target the production database service
(`database:5432/pimascor`). The B2 credentials must be scoped to the
production prefix `pimascor/production`; never reuse the demo key or prefix.
Enable private-bucket server-side encryption in the B2 bucket configuration.

After the source archive has been deployed, create only the missing secrets
interactively as the rootless VPS user:

```bash
cd /var/home/jk/bridge-ph/pimascor/source && ./infra/scripts/provision-production-secrets.sh
```

The helper preserves existing secrets, reads values without putting them in
shell history or source files, and does not print secret contents. The
PostgreSQL password, database URL, and `pgpass` line must refer to the same
database credentials. Podman secrets are mounted when containers are created;
restart the production services after rotating one.

## Deployment

Run on the Mac:

```bash
/Users/jk.deguzman/dev/bridge-ph_Dashboard/production-app/infra/scripts/deploy-production-vps.sh
```

After SSH login, run on the VPS:

```bash
cd /var/home/jk/bridge-ph/pimascor/source && ./infra/scripts/update-production.sh --source /var/home/jk/bridge-ph/pimascor/source
```

This runs forward migrations and starts an empty production database if the
database is new. It does not delete or reset existing production records.

Create the first Administrator interactively:

```bash
cd /var/home/jk/bridge-ph/pimascor/source && ./infra/scripts/provision-production-admin.sh admin admin@delegateops.business "PIMASCOR Administrator"
```

Create additional accounts only after the Administrator signs in and confirms
the person’s role:

```bash
podman exec -it bridge-ph-pimascor-api python -m pimascor_api.seed --username USERNAME --email EMAIL --display-name "DISPLAY NAME" --role GM
podman exec -it bridge-ph-pimascor-api python -m pimascor_api.seed --username USERNAME --email EMAIL --display-name "DISPLAY NAME" --role DCS
podman exec -it bridge-ph-pimascor-api python -m pimascor_api.seed --username USERNAME --email EMAIL --display-name "DISPLAY NAME" --role MICH
podman exec -it bridge-ph-pimascor-api python -m pimascor_api.seed --username USERNAME --email EMAIL --display-name "DISPLAY NAME" --role REQUESTER
```

The production seed command does not create reference clients by default. Add
real client records through the application after the Administrator verifies
the master data.

## Caddy activation

The production updater deliberately leaves the shared edge configuration
unchanged. After reviewing the supplied Caddyfile and confirming the existing
`delegateops.business` site block, run:

```bash
cd /var/home/jk/bridge-ph/pimascor/source && ./infra/scripts/install-production-caddy.sh
```

The script installs the production handler import, adds the production static
web root and proxy network to the existing rootless Caddy Quadlet, validates
Caddy's adapted configuration, restarts Caddy, and checks the public route.
It refuses to edit the file if the expected site block or Quadlet is absent.

## Backup and export

Production installs the PostgreSQL dump, restic backup, retention timer, and
single export worker as separate rootless Quadlets. Full-record archives are
CSV records plus original attachments and generated documents in an encrypted
short-lived archive. The API enforces the two-request Philippine calendar-week
limit; the worker processes the queue and expires archives.

Do not enable production traffic until:

1. all production secrets exist and are scoped correctly;
2. the first Administrator is created;
3. Caddy validation and the HTTPS route check pass;
4. a real client and role account are created;
5. a test quotation, approval, payment, document view, and authorized export
   are verified with the appropriate accounts;
6. backup and restore evidence is recorded separately from the demo.

The architecture follows the official Podman Quadlet user-unit model and
SQLAlchemy's explicit child-before-parent deletion requirement for bulk
operations.
