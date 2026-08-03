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
| GM (Carmel Urot) | `carmel.urot@pimascor.com` | `GM` |
| DCS (Dan C. Subido) | `dan.c.subido@gmail.com` | `DCS` |
| Sales (Leane Tejero) | `leane.tejero@pimascor.com` | `REQUESTER` compatibility role |
| Sales (Romeo Reano) | `romeo.reano@pimascor.com` | `REQUESTER` compatibility role |
| Processor 1 | `processor1@pimascor` | `REQUESTER` compatibility role; document address requires correction |
| Processor 2 | `processor2@pimascor.com` | `REQUESTER` compatibility role |
| Processor 3 | `processor3@pimascor.com` | `REQUESTER` compatibility role |
| Bookkeeper (Mich) | `operations@pimascor.com` | `MICH` |

The document supplies email identities but no separate usernames. The secret
provisioner therefore proposes each email local-part as the username and lets
the operator edit it before the secret is created. Sales and Processor are
business labels in the document; this code maps them to the existing
`REQUESTER` technical role because the current application does not define
separate Sales or Processor permission enums. No new permission is inferred.
The exact `processor1@pimascor` value is retained as supplied and must be
corrected before production activation email can be delivered.

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
source document has an incomplete email for Processor 1, so the helper asks
only for that real address and refuses to continue until it is valid. The
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

After SSH login, run on the VPS:

```bash
cd /var/home/jk/bridge-ph/pimascor/source && ./infra/scripts/provision-production-secrets.sh && ./infra/scripts/update-production.sh --source /var/home/jk/bridge-ph/pimascor/source && ./infra/scripts/install-production-caddy.sh
```

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
7. password recovery is tested with a real mailbox, including an expired link,
   a reused link, a wrong-token attempt, and confirmation that old sessions are
   revoked.

The architecture follows the official Podman Quadlet user-unit model and
SQLAlchemy's explicit child-before-parent deletion requirement for bulk
operations.
