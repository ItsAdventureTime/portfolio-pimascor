#!/usr/bin/env bash
set -Eeuo pipefail

APP_ROOT="${HOME}/bridge-ph/pimascor"
CADDY_CONF_ROOT="${PIMASCOR_CADDY_CONF_ROOT:-}"
CADDY_QUADLET="${PIMASCOR_CADDY_QUADLET:-${HOME}/.config/containers/systemd/caddy/caddy.container}"
SOURCE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CADDYFILE="${CADDY_CONF_ROOT}/Caddyfile"
HANDLERS="${CADDY_CONF_ROOT}/pimascor-production.handlers.Caddyfile"
MARKER='import /etc/caddy/pimascor-production.handlers.Caddyfile'
CADDY_IMAGE=""

if [[ -z "${CADDY_CONF_ROOT}" ]]; then
  for candidate in "${HOME}/caddy/conf" "/home/jk/caddy/conf"; do
    if [[ -f "${candidate}/Caddyfile" ]]; then
      CADDY_CONF_ROOT="${candidate}"
      break
    fi
  done
fi
CADDYFILE="${CADDY_CONF_ROOT}/Caddyfile"
HANDLERS="${CADDY_CONF_ROOT}/pimascor-production.handlers.Caddyfile"

[[ "$(uname -s)" != "Darwin" ]] || { printf '%s\n' 'Run this on the Fedora CoreOS VPS.' >&2; exit 1; }
[[ "${EUID}" -ne 0 ]] || { printf '%s\n' 'Refusing to run as root.' >&2; exit 1; }
[[ -f "${CADDYFILE}" ]] || { printf 'Caddyfile not found: %s\n' "${CADDYFILE}" >&2; exit 1; }
[[ -f "${CADDY_QUADLET}" ]] || { printf 'Caddy Quadlet not found: %s\n' "${CADDY_QUADLET}" >&2; exit 1; }
[[ -f "${SOURCE_ROOT}/infra/caddy/pimascor-production.handlers.Caddyfile" ]] || { printf '%s\n' 'Production Caddy handlers are missing from the committed source.' >&2; exit 1; }
grep -Eq '^delegateops\.business[[:space:]]*\{' "${CADDYFILE}" || { printf '%s\n' 'Expected delegateops.business site block was not found; refusing to edit Caddy.' >&2; exit 1; }
[[ -d "${APP_ROOT}/web-dist" ]] || { printf 'Production web root not found: %s\n' "${APP_ROOT}/web-dist" >&2; exit 1; }
CADDY_IMAGE="$(awk -F= '/^Image=/{print $2; exit}' "${CADDY_QUADLET}")"
[[ -n "${CADDY_IMAGE}" ]] || { printf '%s\n' 'Caddy image was not found in the shared Caddy Quadlet.' >&2; exit 1; }

install -d -m 700 "${CADDY_CONF_ROOT}"
install -m 600 "${SOURCE_ROOT}/infra/caddy/pimascor-production.handlers.Caddyfile" "${HANDLERS}"

# Keep one canonical import. A legacy relative import would load the same
# production handlers twice after the absolute import below is installed.
if grep -Eq '^[[:space:]]*import[[:space:]]+pimascor-production\.handlers\.Caddyfile[[:space:]]*$' "${CADDYFILE}"; then
  caddy_tmp="$(mktemp "${CADDYFILE}.next.XXXXXX")"
  awk '
    /^[[:space:]]*import[[:space:]]+pimascor-production\.handlers\.Caddyfile[[:space:]]*$/ { next }
    { print }
  ' "${CADDYFILE}" > "${caddy_tmp}"
  chmod 600 "${caddy_tmp}"
  mv "${caddy_tmp}" "${CADDYFILE}"
fi

if ! grep -Fq "${MARKER}" "${CADDYFILE}"; then
  caddy_tmp="$(mktemp "${CADDYFILE}.next.XXXXXX")"
  awk -v marker="${MARKER}" '
    !inserted && $0 ~ /^delegateops\.business[[:space:]]*\{/ {
      print
      print "    " marker
      inserted=1
      next
    }
    { print }
    END { if (!inserted) exit 3 }
  ' "${CADDYFILE}" > "${caddy_tmp}"
  chmod 600 "${caddy_tmp}"
  mv "${caddy_tmp}" "${CADDYFILE}"
fi

# caddy fmt makes only presentation changes; caddy validate catches syntax and
# provisioning errors before the shared edge service is restarted. Both run in
# disposable containers so no tooling is installed on the Fedora CoreOS host.
podman run --rm --network none \
  --volume "${CADDY_CONF_ROOT}:/etc/caddy:Z" \
  "${CADDY_IMAGE}" \
  caddy fmt --overwrite /etc/caddy/Caddyfile
podman run --rm --network none \
  --volume "${CADDY_CONF_ROOT}:/etc/caddy:ro,Z" \
  "${CADDY_IMAGE}" \
  caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile

if awk '
  /^Volume=.*:\/srv\/bridge-ph-pimascor(:|$)/ &&
    $0 != "Volume=%h/bridge-ph/pimascor/web-dist:/srv/bridge-ph-pimascor:ro,Z" { found=1 }
  END { exit(found ? 0 : 1) }
' "${CADDY_QUADLET}"; then
  quadlet_tmp="$(mktemp "${CADDY_QUADLET}.next.XXXXXX")"
  awk '
    /^Volume=.*:\/srv\/bridge-ph-pimascor(:|$)/ { next }
    { print }
  ' "${CADDY_QUADLET}" > "${quadlet_tmp}"
  chmod 600 "${quadlet_tmp}"
  mv "${quadlet_tmp}" "${CADDY_QUADLET}"
fi

if ! grep -Fq 'Network=bridge-ph-pimascor-proxy.network' "${CADDY_QUADLET}" ||
  ! grep -Fxq 'Volume=%h/bridge-ph/pimascor/web-dist:/srv/bridge-ph-pimascor:ro,Z' "${CADDY_QUADLET}"; then
  quadlet_tmp="$(mktemp "${CADDY_QUADLET}.next.XXXXXX")"
  awk '
    /^\[Service\]/ && !settings_added {
      if (!network_seen) print "Network=bridge-ph-pimascor-proxy.network"
      if (!web_volume_seen) print "Volume=%h/bridge-ph/pimascor/web-dist:/srv/bridge-ph-pimascor:ro,Z"
      settings_added=1
    }
    /^Network=bridge-ph-pimascor-proxy\.network$/ { network_seen=1 }
    /^Volume=%h\/bridge-ph\/pimascor\/web-dist:\/srv\/bridge-ph-pimascor:ro,Z$/ { web_volume_seen=1 }
    { print }
    END { if (!settings_added) exit 3 }
  ' "${CADDY_QUADLET}" > "${quadlet_tmp}"
  chmod 600 "${quadlet_tmp}"
  mv "${quadlet_tmp}" "${CADDY_QUADLET}"
fi

# Caddy is shared by several sites. Do not conceal a missing unrelated source
# by creating an empty directory or removing a mount that its Caddy route uses.
missing_mounts=()
while IFS= read -r source; do
  [[ -n "${source}" && -e "${source}" ]] || missing_mounts+=("${source}")
done < <(
  awk -v home="${HOME}" '
    /^Volume=\// {
      source=$0
      sub(/^Volume=/, "", source)
      sub(/:.*/, "", source)
      print source
    }
    /^Volume=%h\// {
      source=$0
      sub(/^Volume=%h/, home, source)
      sub(/:.*/, "", source)
      print source
    }
  ' "${CADDY_QUADLET}"
)
if ((${#missing_mounts[@]})); then
  printf '%s\n' 'Shared Caddy Quadlet has missing host bind-mount source(s); refusing to restart it:' >&2
  printf '  %s\n' "${missing_mounts[@]}" >&2
  printf '%s\n' 'Restore the owning site directory or remove its route and mount together before retrying.' >&2
  exit 1
fi

systemctl --user daemon-reload
systemctl --user restart bridge-ph-pimascor-proxy-network.service
systemctl --user restart caddy.service
podman exec caddy caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
curl --fail --silent --show-error --location --max-time 15 "https://delegateops.business/pimascor/" >/dev/null
printf '%s\n' 'Production Caddy route is active at https://delegateops.business/pimascor/'
