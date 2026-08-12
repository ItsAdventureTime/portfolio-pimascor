#!/usr/bin/env bash
set -Eeuo pipefail

# Podman recursively scans these rootless Quadlet roots. Remove only the known
# obsolete accustandard unit before any systemctl call can invoke the generator.
# Never remove its data volume or an administrator-owned unit.
roots=(
  "${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/containers/systemd"
  "${XDG_CONFIG_HOME:-${HOME}/.config}/containers/systemd"
  "/etc/containers/systemd/users/$(id -u)"
  "/etc/containers/systemd/users"
  "/usr/share/containers/systemd/users/$(id -u)"
  "/usr/share/containers/systemd/users"
)

scan_file="$(mktemp "${TMPDIR:-/tmp}/pimascor-legacy-quadlet.XXXXXX")"
trap 'rm -f -- "${scan_file}"' EXIT

for root in "${roots[@]}"; do
  [[ -d "${root}" ]] || continue
  if ! find -P "${root}" \( -type f -o -type l \) \
    -name 'accustandard-demo-db.container' -print0 >>"${scan_file}"; then
    printf 'Refusing to continue: could not scan Quadlet root: %s\n' "${root}" >&2
    exit 1
  fi
done

matching_quadlets=()
while IFS= read -r -d '' quadlet; do
  grep -Fqx 'Image=postgres:16-alpine' "${quadlet}" || continue
  owner="$(stat -c '%u' "${quadlet}")" || {
    printf 'Refusing to continue: could not inspect Quadlet ownership: %s\n' "${quadlet}" >&2
    exit 1
  }
  parent="$(dirname -- "${quadlet}")"
  if [[ "${owner}" != "$(id -u)" || ! -w "${parent}" ]]; then
    printf 'Refusing to continue: administrator-owned legacy Quadlet: %s\n' "${quadlet}" >&2
    printf '%s\n' 'Remove or update that exact Quadlet as an administrator, then rerun this updater.' >&2
    exit 1
  fi
  matching_quadlets+=("${quadlet}")
done <"${scan_file}"

removed=false
for quadlet in "${matching_quadlets[@]}"; do
  printf 'Retiring legacy accustandard Quadlet: %s\n' "${quadlet}"
  rm -f -- "${quadlet}"
  removed=true
done

if [[ "${removed}" == true ]]; then
  systemctl --user disable --now accustandard-demo-db.service >/dev/null 2>&1 || true
  podman rm -f accustandard-demo-db >/dev/null 2>&1 || true
  systemctl --user daemon-reload
fi
