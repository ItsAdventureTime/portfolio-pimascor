#!/usr/bin/env bash
set -Eeuo pipefail

# Writes a non-sensitive local catalog entry only after the backup service exits
# successfully. The encrypted Restic repository remains the source of truth.
APP_ROOT="${HOME}/bridge-ph/pimascor"
CATALOG_ROOT="${APP_ROOT}/backup-catalog"
HISTORY_ROOT="${CATALOG_ROOT}/history"
completed_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
backup_id="production-${completed_at//[^0-9]/}"
entry="${HISTORY_ROOT}/${backup_id}.json"

install -d -m 700 "${HISTORY_ROOT}"
tmp="$(mktemp "${CATALOG_ROOT}/.entry.XXXXXX")"
trap 'rm -f -- "${tmp}"' EXIT
cat >"${tmp}" <<EOF
{
  "id": "${backup_id}",
  "completed_at": "${completed_at}",
  "scope": "PostgreSQL dump, production uploads, and production Quadlets",
  "encrypted": true,
  "storage": "Backblaze B2 encrypted Restic repository",
  "retention_class": "daily/weekly/monthly; yearly snapshots up to 5 years; legal holds take precedence",
  "local_copy_deleted": true,
  "restore_mode": "CLI only",
  "verification": "backup service completed successfully"
}
EOF
chmod 600 "${tmp}"
mv -f -- "${tmp}" "${entry}"
ln -sfn "${entry}" "${CATALOG_ROOT}/latest.json"

# Catalog metadata is not a backup. Keep only the operational history needed
# by the UI; the encrypted B2 repository retains the actual recovery material.
find "${HISTORY_ROOT}" -type f -name 'production-*.json' -mtime +90 -delete
