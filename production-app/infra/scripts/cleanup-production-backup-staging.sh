#!/usr/bin/env bash
set -Eeuo pipefail

APP_ROOT="${HOME}/bridge-ph/pimascor"
STAGING_ROOT="${APP_ROOT}/backup-staging"

[[ "$(uname -s)" != "Darwin" ]] || { printf '%s\n' 'Run this on the Fedora CoreOS VPS.' >&2; exit 1; }
[[ "${EUID}" -ne 0 ]] || { printf '%s\n' 'Use the rootless jk account.' >&2; exit 1; }

# Invoked by the successful Restic backup unit only; failed uploads retain the
# dump for investigation and a manual retry.
rm -f -- "${STAGING_ROOT}/postgres.dump"
