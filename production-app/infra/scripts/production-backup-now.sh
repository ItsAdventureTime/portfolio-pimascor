#!/usr/bin/env bash
set -Eeuo pipefail

APP_ROOT="${HOME}/bridge-ph/pimascor"
STAGING_ROOT="${APP_ROOT}/backup-staging"

[[ "$(uname -s)" != "Darwin" ]] || { printf '%s\n' 'Run this on the Fedora CoreOS VPS.' >&2; exit 1; }
[[ "${EUID}" -ne 0 ]] || { printf '%s\n' 'Use the rootless jk account.' >&2; exit 1; }
command -v systemctl >/dev/null || { printf '%s\n' 'Missing systemctl.' >&2; exit 1; }

dry_run=false
while (($#)); do
  case "$1" in
    --dry-run) dry_run=true; shift ;;
    --help|-h)
      printf '%s\n' 'Usage: production-backup-now.sh [--dry-run]'
      printf '%s\n' 'Creates a consistent PostgreSQL dump and uploads it with Restic.'
      exit 0
      ;;
    *) printf 'Unknown option: %s\n' "$1" >&2; exit 2 ;;
  esac
done

if "${dry_run}"; then
  printf '%s\n' 'DRY RUN: would start PostgreSQL dump, then encrypted B2 Restic backup.'
  printf 'DRY RUN: local staging would be cleared only after service success: %s\n' "${STAGING_ROOT}"
  exit 0
fi

systemctl --user start --wait bridge-ph-pimascor-db-dump.service
systemctl --user start --wait bridge-ph-pimascor-backup.service

# The backup unit succeeded only after Restic uploaded and verified its pack
# files. Remove the transient dump so it cannot accumulate on the VPS.
find "${STAGING_ROOT}" -mindepth 1 -maxdepth 1 -type f -delete
printf '%s\n' 'Production backup completed and transient local staging was removed.'
