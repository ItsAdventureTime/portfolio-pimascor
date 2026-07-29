#!/usr/bin/env bash
set -Eeuo pipefail

# Removes only stale static-build directories created by the earlier, incorrect
# updater path. The live demo web root remains ~/bridge-ph/pimascor-demo.

APP_ROOT="${HOME}/pimascor-demo"
WEB_ROOT="${HOME}/bridge-ph/pimascor-demo"
CONTAINER_WEB_ROOT="/srv/bridge-ph-pimascor-demo"

[[ "$(uname -s)" != "Darwin" ]] || {
  printf '%s\n' 'This is a VPS-only reconciliation helper.' >&2
  exit 1
}
[[ "${EUID}" -ne 0 ]] || {
  printf '%s\n' 'Refusing to run as root: use the rootless Linux user that owns Caddy.' >&2
  exit 1
}
[[ -f "${WEB_ROOT}/web-dist/index.html" ]] || {
  printf 'Refusing cleanup: expected live web root is missing %s/web-dist/index.html.\n' "${WEB_ROOT}" >&2
  exit 1
}

expected_mount="${WEB_ROOT}/web-dist -> ${CONTAINER_WEB_ROOT}"
actual_mounts="$(podman inspect caddy --format '{{range .Mounts}}{{println .Source "->" .Destination}}{{end}}')"
[[ "${actual_mounts}" == *"${expected_mount}"* ]] || {
  printf 'Refusing cleanup: Caddy is not mounted from %s.\n' "${expected_mount}" >&2
  exit 1
}

find "${APP_ROOT}" -maxdepth 1 -mindepth 1 -type d \
  \( -name 'web-dist' -o -name 'web-dist.next.*' -o -name 'web-dist.previous.*' \) \
  -print -exec rm -rf -- {} +

printf '%s\n' 'Removed only obsolete static-build directories under ~/pimascor-demo.'
