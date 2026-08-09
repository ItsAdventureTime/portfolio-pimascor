# PIMASCOR production deployment

This is the isolated production track. It does not use the demo runtime, demo
database, demo object prefix, demo containers, or demo web root.

For a client/operator transfer of the hosted service, use
`docs/HANDOFF-BRIDGE-PIMASCOR.md`. This deployment runbook is the technical
reference behind that handoff; it is not a substitute for the access-transfer,
acceptance, privacy, or support records.

Runtime paths:

- `~/bridge-ph/pimascor`: production source, web assets, PostgreSQL data,
  upload spool, backup staging, and restic cache.
- `~/.config/containers/systemd/bridge-ph/pimascor`: production Quadlets.
- Caddy serves `~/bridge-ph/pimascor/web-dist` at
  `https://delegateops.business/pimascor/`.

Caddy is not host-installed or root-run. It is the existing rootless Podman
container managed by the user-level, Quadlet-generated `caddy.service`, with
its source Quadlet at `~/.config/containers/systemd/caddy/caddy.container`.
Run all Caddy lifecycle commands as VPS user `jk` with `systemctl --user`; do
not use `sudo systemctl`, a system-level `caddy.service`, or a host `caddy`
binary. The generated service creates the established `caddy` container name,
which is used only for post-start inspection.

The production API uses `DEPLOYMENT_TIER=production`,
`APP_ENV=production`, private B2 storage, HTTPS-only cookies, Resend email,
and the durable export worker. It never runs `demo_reset` and does not seed
fictional clients or transactions.

The authenticated workspace also provides a compact, dismissible PWA
installation reminder. It is shown after sign-in—not on the login screen—and
gives users platform-specific instructions for Safari on iPhone/iPad, Chrome
on Android, and compatible desktop Chromium browsers. It is hidden when a
standalone, fullscreen, minimal-ui, or window-controls-overlay display mode is
detected. See `docs/PWA-INSTALLATION.md` for the user-facing handout.
Installing the PWA does not change authentication, role permissions, session
expiry, or document privacy.

After a user-facing release, the latest plain-language update appears once per
user after authentication. The acknowledgement is stored with the production
user record, so the update does not repeat on every login or on another device.
Maintain the release entry and date in `docs/RELEASE-NOTES.md` together with
the matching application release record.

## Production roles

The production policy from Section 1 of the owner correction document is:

| Role | Production authority |
| --- | --- |
| Admin | Full administration and attributable superuser access. |
| GM | Operational superuser except Administrator-only controls; approves and can release DCS Payment. |
| DCS | Executes DCS Payment and can override GM-owned approvals with an attributable reason. |
| Mich | Bookkeeper/reviewer; prepares accounting work, reviews/close Liquidations, and can export authorized records. |
| Requester | Creates and submits assigned operational requests; no management profitability, export, or payment authority. |

The same Section 1 document identifies these production accounts:

| Document identity | Email | Technical role used by this build |
| --- | --- | --- |
| Admin (Team) | `team@bridge-ph.com` | `ADMIN` |
| Admin (Alyssa) | `Alyssa.d@bridge-ph.com` | `ADMIN` |
| GM (Carmel C. Urot) | `carmel.urot@gmail.com` | `GM` |
| DCS/CEO/Chairman (Atty. Daniel C. Subido) | `dan.c.subido@gmail.com` | `DCS` |
| Sales (Leane Tejero) | `leane.tejero@pimascor.com` | `REQUESTER` compatibility role |
| Sales (Romeo Reano) | `romeo.reano@pimascor.com` | `REQUESTER` compatibility role |
| Processor (Marcelo Sabando) | `processor1@pimascor.com` | `REQUESTER` compatibility role |
| Processor (Christian Arcangel) | `processor2@pimascor.com` | `REQUESTER` compatibility role |
| Processor (Jaycee Dimandal) | `processor3@pimascor.com` | `REQUESTER` compatibility role |
| Bookkeeper (Michelle Umpacuman) | `operations@pimascor.com` | `MICH` |

The document supplies email identities but no separate usernames. The secret
provisioner therefore proposes each email local-part as the username and lets
the operator edit it before the secret is created. Sales and Processor are
business labels in the document; this code maps them to the existing
`REQUESTER` technical role because the current application does not define
separate Sales or Processor permission enums. No new permission is inferred.
The DCS, CEO, and Chairman labels identify the same person and remain one
technical `DCS` role.

The GM/DCS escalation policy is enabled only when `DEPLOYMENT_TIER=production`;
the demo keeps its existing role policy.

## Password lifecycle

Production does not pre-create role accounts and does not generate passwords
automatically. The production bootstrap manifest creates the Administrator,
GM, DCS, Mich, and Requester accounts from a rootless Podman secret. The
manifest contains only usernames, email addresses, display names, and roles;
it contains no passwords. New accounts are marked as pending activation.

On the user's first access, PIMASCOR sends a one-time email code. After the
code is verified, the user chooses a password of at least 12 characters in the
application. PIMASCOR does not email a permanent or generated password. The
database stores an Argon2 password hash, not the plaintext password, so an
existing password cannot be retrieved.

After activation, normal sign-in requires the password and then a one-time
email code sent through the configured production email provider. If a user
forgets a password, select **Forgot password?** on the sign-in screen and
submit the username or email. The API always returns the same message for
known, unknown, disabled, pending, and rate-limited accounts. An eligible
activated user receives a single-use reset link that expires in 15 minutes;
the link is kept in the URL fragment so it is not sent in HTTP requests or
referrer headers. The user chooses a new password of at least 12 characters,
then signs in again. Every existing session is revoked after a successful
reset. Pending first-login accounts must use account activation instead.

If a password is suspected to be exposed and email recovery is unavailable,
an Administrator can reset it from the VPS and revoke that account's active
sessions:

```bash
podman exec -it bridge-ph-pimascor-api python -m pimascor_api.account_admin set-password USERNAME
```

This is a reset, not a retrieval operation. The command prompts for the new
password and confirms it without placing it in shell history.

Reset requests are persisted with hashed identifier/source values and limited
to three per identifier and twenty per source in a rolling 60-minute window.
Reset tokens are cryptographically random, stored only as SHA-256 hashes,
single-use, attempt-limited, and never written to logs or audit reasons.

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
bridge_ph_pimascor_account_bootstrap
```

The database URL must target the production database service
(`database:5432/pimascor`). The B2 credentials must be scoped to the
production prefix `pimascor/production`; never reuse the demo key or prefix.
Enable private-bucket server-side encryption in the B2 bucket configuration.

The PostgreSQL data store intentionally remains a bind mount at
`~/bridge-ph/pimascor/data/postgres/18/docker`, with `:U,Z` ownership and SELinux
relabeling. A named `.volume` would move the live database outside the required
production data tree and outside the host-side recovery layout; database dumps
are already captured separately. PostgreSQL 18 startup is allowed only the
minimal `CHOWN`, `FOWNER`, `DAC_OVERRIDE`, `SETUID`, and `SETGID` capabilities
needed by the official entrypoint to prepare the bind mount and drop from its
initialization user to the `postgres` server user.

`bridge_ph_pimascor_restic_password` is the encryption key for the Restic
repository stored in Backblaze B2. It is not the PostgreSQL password, a VPS
login password, or a B2 access key. Store it in the approved password manager;
without it, encrypted backup snapshots cannot be restored. The updater enables
the backup timers only after the production services are active.

After the source archive has been deployed, create only the missing secrets as
the rootless VPS user:

```bash
cd /var/home/jk/bridge-ph/pimascor/source && ./infra/scripts/provision-production-secrets.sh
```

The helper preserves existing secrets, reads values without putting them in
shell history or source files, and does not print secret contents. It asks for
the PostgreSQL password once, then derives the matching database URL and
`pgpass` secrets from it. If the PostgreSQL secret already exists (including a
partially completed earlier run), the helper reads it through Podman's
`--showsecret` interface and completes the derived secrets without asking you
to type the password again. Podman secrets are mounted when containers are
created; restart the production services after rotating one.

The helper also creates `bridge_ph_pimascor_account_bootstrap` from the ten
documented Section 1 accounts without repeating ten sets of prompts. The
production account-bootstrap Quadlet consumes the secret after migrations and
creates or verifies the pending accounts idempotently. It never accepts or
stores an initial password. Use `--interactive-account-manifest` only when you
intentionally need to override the documented defaults.

The bootstrap container imports the same production settings validation as the
API. The deployment source therefore includes its HTTPS public URL,
`EMAIL_PROVIDER=resend`, secure-cookie setting, and the
`bridge_ph_pimascor_resend_api_key` Podman secret. `update-production.sh`
preflights these values before changing services; a missing value is a source
configuration error, not a reason to weaken production validation.

If an older five-account manifest was already created, refresh only that
manifest with:

```bash
cd /var/home/jk/bridge-ph/pimascor/source && ./infra/scripts/provision-production-secrets.sh --replace-account-manifest
```

To replace the manifest with custom usernames, emails, and display names, add
`--interactive-account-manifest`; otherwise the documented defaults are used.

## Deployment

Run on the Mac:

```bash
/Users/jk.deguzman/dev/bridge-ph_Dashboard/production-app/infra/scripts/deploy-production-vps.sh
```

The Mac-side script archives the committed `production-app` tree and transfers
it to `/var/home/jk/bridge-ph/pimascor/source`. It does not transfer secrets,
PostgreSQL data, uploads, backups, or the demo tree. Repeat it for every
committed production release. When the approved account names, email
addresses, or roles change, use the explicit account-refresh option:

```bash
/Users/jk.deguzman/dev/bridge-ph_Dashboard/production-app/infra/scripts/deploy-production-vps.sh --refresh-account-manifest
```

That option replaces only the account-bootstrap Podman secret. It does not
replace passwords or existing user sessions. The subsequent production update
re-runs the bootstrap idempotently; already-correct accounts are unchanged and
new or corrected pending accounts are reconciled. An already-activated account
whose email, display name, or role differs is refused for safety and must be
changed through an explicit Administrator procedure.

After SSH login, run on the VPS:

```bash
cd /var/home/jk/bridge-ph/pimascor/source && ./infra/scripts/provision-production-secrets.sh && ./infra/scripts/update-production.sh --source /var/home/jk/bridge-ph/pimascor/source && ./infra/scripts/install-production-caddy.sh
```

The normal repeatable sequence is to run the Mac transfer script, then run
`update-production.sh` on the VPS. Migrations execute through `alembic upgrade
head`: each revision runs once because Alembic records it in the database.
The account bootstrap, service restarts, web asset replacement, and backup
timer activation are safe to repeat. Secret provisioning preserves existing
secrets unless the explicit account-manifest replacement option is used.

The first production activation also creates the host backup-catalog directory,
installs the post-success catalog hook, and installs the backup/restore helper
scripts. Those filesystem setup steps are idempotent; later releases refresh
the scripts and Quadlets without deleting the catalog history or production
data. The first real backup creates the first catalog entry. No restore runs
automatically during deployment.

Local macOS builds are optional validation only. The deployment script builds
the production images on the VPS with its rootless Podman runtime. If local
validation is needed, use the existing Podman machine and disposable
`podman run --rm` containers; do not install production secrets or data on the
Mac.

This is the complete VPS sequence. Secret provisioning preserves existing
secrets and only prompts for missing values. The updater builds and activates
the production API, web assets, migrations, account bootstrap, export worker,
and backup timers. The final command must be invoked as
`./infra/scripts/install-production-caddy.sh` from the deployed source
directory; `install-production-caddy.sh` by itself is not a shell command
unless that directory has been added to `PATH`.

This runs forward migrations and starts an empty production database if the
database is new. It does not delete or reset existing production records.

The account-bootstrap Quadlet creates all ten Section 1 accounts during the
production update. The Administrator can then review the accounts and their
roles in the application. For an emergency manual account, the legacy helper
`infra/scripts/provision-production-admin.sh` remains available and prompts
for a password; it is not part of the automatic bootstrap path.

Create additional manual accounts only after the Administrator confirms the
person’s role:

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
It refuses to edit the file if the expected site block, Quadlet, or production
web root is absent. It normalizes the PIMASCOR web mount to the canonical
`%h/bridge-ph/pimascor/web-dist` source and removes only duplicate PIMASCOR
mounts that target the same container directory. It never removes, creates, or
changes an unrelated Caddy site. It also removes the exact legacy relative
`import pimascor-production.handlers.Caddyfile` line if present, leaving the
single canonical absolute import installed by the production route.

Before any Caddy restart, the installer runs the official `caddy fmt
--overwrite` command against the shared Caddyfile, then runs `caddy validate`
in a disposable `podman run --rm` container using the exact Caddy image declared
by the shared Quadlet. Formatting standardizes whitespace and indentation only;
it does not invent routes, repair missing directories, change proxy targets, or
alter security policy. Validation adapts and provisions the configuration
without starting it, so syntax, import, and provisioning failures stop the
activation before the live edge service is affected.

The installer verifies that the user-level `caddy.service` is loaded before it
changes the shared configuration. It reloads the Quadlet generator with
`systemctl --user daemon-reload`, restarts `caddy.service`, and validates the
running rootless container afterward. It does not use `caddy reload`, which
would bypass the intended Quadlet lifecycle. After restart it polls the
production API health endpoint for up to 60 seconds, so a normal API warm-up
does not produce a false deployment failure or invite an immediate CDN purge.
Expected intermediate `502` responses are suppressed during that bounded
readiness window; only an exhausted health check is reported as an activation
failure.

Podman fails a container start when a bind-mount source does not exist. A
`statfs ... no such file or directory` message with exit status 125 therefore
indicates a missing host mount in the shared Caddy Quadlet, not a failed web
build or invalid application Caddyfile. The installer preflights every shared
Caddy host mount and names missing sources before it attempts a restart.

The preflight does not create placeholder directories or remove another site's
route. If it reports a missing source, correct that owning site's deployment or
retire its route and mount together as a separate, explicitly approved change.

After the owning site is corrected, re-run the installer from the deployed
production source:

```bash
cd /var/home/jk/bridge-ph/pimascor/source && ./infra/scripts/install-production-caddy.sh
systemctl --user status --no-pager caddy.service
journalctl --user -u caddy.service --no-pager --lines=80
```

Inspect any other missing `Volume=` source reported by the preflight and
correct its owning site or Quadlet explicitly.

## Backup and export

Production installs the PostgreSQL dump, restic backup, retention timer, and
single export worker as separate rootless Quadlets. Full-record archives are
CSV records plus original attachments and generated documents in an encrypted
short-lived archive. The API enforces the two-request Philippine calendar-week
limit; the worker processes the queue and expires archives.

### Recovery policy and operator controls

The encrypted Backblaze B2 Restic repository is the recovery source of truth.
The scheduled service creates a consistent PostgreSQL custom-format dump,
backs up production uploads, the dump, and production Quadlets, then records a
non-sensitive completion entry for the Admin/DCS catalog. The transient dump is
deleted only after the Restic service exits successfully. B2 credentials and
the Restic password never enter the catalog or the web response.

The current base-backup schedule is four fixed runs per day. It is deliberately
not an adaptive 1-hour/2-hour/4-hour policy: predictable schedules are easier
to audit and restore. Near-real-time PostgreSQL WAL archiving/PITR remains a
separate production change requiring a tested archive destination and restore
rehearsal; this release does not claim WAL/PITR availability.

Retention is applied by the Restic timer (short daily, weekly, monthly, and
yearly classes). Quarterly and semiannual legal retention must be represented
by approved tagged/archive copies or a B2 lifecycle/Object Lock policy; Restic
`forget` alone does not create those business calendar tiers. A legal hold
must be approved before enabling immutable retention because Object Lock can
prevent lifecycle deletion.

Admin and DCS can view the encrypted backup completion catalog under Accounting.
They cannot restore, replace, delete, or re-encrypt production data from the
web app. Only the service owner uses the VPS CLI, and every restore starts as a
dry run and then a quarantine restore for inspection.

Force a backup on the VPS:

```bash
cd /var/home/jk/bridge-ph/pimascor/source && ./infra/scripts/production-backup-now.sh --dry-run
cd /var/home/jk/bridge-ph/pimascor/source && ./infra/scripts/production-backup-now.sh
```

List encrypted repository snapshots, then perform a safe dry run (the default)
before any download:

```bash
cd /var/home/jk/bridge-ph/pimascor/source && ./infra/scripts/production-restore.sh --list
cd /var/home/jk/bridge-ph/pimascor/source && ./infra/scripts/production-restore.sh --snapshot latest --dry-run
```

After reviewing the snapshot and approving a target directory, restore only to
quarantine. The script refuses the live production root:

```bash
cd /var/home/jk/bridge-ph/pimascor/source && ./infra/scripts/production-restore.sh --snapshot SNAPSHOT_ID --target /var/home/jk/bridge-ph/pimascor/restore-quarantine --execute
```

Review checksums, database contents, migrations, and uploaded files before a
separate controlled cutover. There is intentionally no restore button or
restore API endpoint.

Do not enable production traffic until:

1. all production secrets exist and are scoped correctly;
2. the first Administrator is created;
3. Caddy validation and the HTTPS route check pass;
4. a real client and role account are created;
5. a test quotation, approval, payment, document view, and authorized export
   are verified with the appropriate accounts;
6. backup and restore evidence is recorded separately from the demo.
7. password recovery is tested with a real mailbox, including an expired link,
   a reused link, a wrong-token attempt, and confirmation that old sessions are
   revoked.
8. the owner runs the force-backup dry run, confirms a completed catalog entry,
   lists snapshots, and rehearses a quarantine restore before production data
   is considered recoverable.

The architecture follows the official Podman Quadlet user-unit model and
SQLAlchemy's explicit child-before-parent deletion requirement for bulk
operations.
