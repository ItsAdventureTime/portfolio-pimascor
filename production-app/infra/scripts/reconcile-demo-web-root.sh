#!/usr/bin/env bash
set -Eeuo pipefail

# Removes stale static-build staging directories from the canonical demo root.

APP_ROOT="${HOME}/bridge-ph/pimascor-demo"
WEB_ROOT="${APP_ROOT}"
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

expected_web_root="$(realpath "${WEB_ROOT}/web-dist")"
actual_web_root="$(podman inspect caddy --format "{{range .Mounts}}{{if eq .Destination \"${CONTAINER_WEB_ROOT}\"}}{{.Source}}{{end}}{{end}}")"
[[ -n "${actual_web_root}" ]] || {
  printf 'Refusing cleanup: Caddy has no mount at %s.\n' "${CONTAINER_WEB_ROOT}" >&2
  exit 1
}
actual_web_root="$(realpath "${actual_web_root}")"
[[ "${actual_web_root}" == "${expected_web_root}" ]] || {
  printf 'Refusing cleanup: Caddy mount resolves to %s; expected %s.\n' \
    "${actual_web_root}" "${expected_web_root}" >&2
  exit 1
}

find "${WEB_ROOT}" -maxdepth 1 -mindepth 1 -type d \
  -name 'web-dist.next.*' -print -exec rm -rf -- {} +

printf '%s\n' 'Removed only stale build staging directories from the canonical demo root.'
