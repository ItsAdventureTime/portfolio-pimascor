# Production backup and restore runbook

This runbook applies only to `~/bridge-ph/pimascor`. It is separate from the
demo runtime and from the Git continuity runbook.

## Responsibilities

- The backup timer creates encrypted Restic snapshots in private Backblaze B2.
- The API exposes non-sensitive completion metadata to Admin and DCS.
- Admin and DCS cannot restore, replace, delete, or download repository data
  from the web app.
- The service owner performs recovery from the VPS CLI, beginning with a dry
  run and a quarantine restore.

## What is backed up

Each successful run includes the PostgreSQL custom-format dump, production
upload spool, and production Quadlets. The PostgreSQL dump includes
`support_tickets`, replies, portal-token hashes, assignment/status history,
and attachment metadata. The local dump is removed only after the Restic
service completes successfully.

Support attachment bytes live in the private Backblaze B2 production prefix;
they are not copied into the host-side Restic snapshot. This is intentional:
attachments are short-lived support evidence and are deleted from B2 when a
ticket closes. A restore therefore recovers the ticket conversation and
metadata, but not an already-removed attachment object. If policy later
requires attachment recovery, add a separately encrypted B2 object backup and
restore rehearsal before claiming that capability.

The current release provides fixed scheduled base backups and Restic
deduplication. It does not claim continuous WAL/PITR until PostgreSQL WAL
archiving has a separately tested destination and restore rehearsal.

## Operator checks

Run as the rootless VPS user `jk`:

```bash
cd /var/home/jk/bridge-ph/pimascor/source && ./infra/scripts/production-backup-now.sh --dry-run
cd /var/home/jk/bridge-ph/pimascor/source && ./infra/scripts/production-backup-now.sh
systemctl --user list-timers 'bridge-ph-pimascor-backup*'
```

Do not delete the Restic password secret. It is required to decrypt the
repository and cannot be reconstructed from the database password or B2 key.

## Restore procedure

1. Preserve the incident reference and stop application changes.
2. List snapshots without downloading data:

   ```bash
   cd /var/home/jk/bridge-ph/pimascor/source && ./infra/scripts/production-restore.sh --list
   ```

3. Run the default dry run and confirm the selected snapshot and quarantine
   target:

   ```bash
   cd /var/home/jk/bridge-ph/pimascor/source && ./infra/scripts/production-restore.sh --snapshot SNAPSHOT_ID --dry-run
   ```

4. Restore to a new quarantine directory only:

   ```bash
   cd /var/home/jk/bridge-ph/pimascor/source && ./infra/scripts/production-restore.sh --snapshot SNAPSHOT_ID --target /var/home/jk/bridge-ph/pimascor/restore-quarantine --execute
   ```

5. Verify the dump checksum, run `pg_restore --list`, inspect uploads, check
   the expected migration head, and compare the catalog entry with service
   logs.
6. Obtain owner approval for a controlled cutover. The script intentionally
   refuses to overwrite the live production root and does not stop services.

## Retention and legal hold

The operational policy keeps recent daily, weekly, monthly, and five yearly
classes. Quarterly and semiannual five-year records require approved tagged
archive copies or B2 lifecycle/Object Lock configuration. Object Lock is not
enabled by this repository because its immutability can conflict with approved
deletion and legal-hold workflows. Document any legal hold before changing
retention.

## Evidence

Record the date/time, operator, snapshot ID, command mode, checksum results,
quarantine path, and approval in the production change record. Never record
Podman secret contents, Restic passwords, B2 application keys, or reset tokens.
