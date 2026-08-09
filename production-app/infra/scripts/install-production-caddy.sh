#!/usr/bin/env bash
set -Eeuo pipefail

APP_ROOT="${HOME}/bridge-ph/pimascor"
CADDY_CONF_ROOT="${PIMASCOR_CADDY_CONF_ROOT:-}"
CADDY_QUADLET="${PIMASCOR_CADDY_QUADLET:-${HOME}/.config/containers/systemd/caddy/caddy.container}"
SOURCE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CADDYFILE="${CADDY_CONF_ROOT}/Caddyfile"
HANDLERS="${CADDY_CONF_ROOT}/pimascor-production.handlers.Caddyfile"
MARKER='import /etc/caddy/pimascor-production.handlers.Caddyfile'

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

install -d -m 700 "${CADDY_CONF_ROOT}"
install -m 600 "${SOURCE_ROOT}/infra/caddy/pimascor-production.handlers.Caddyfile" "${HANDLERS}"

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

if ! grep -Fq 'Network=bridge-ph-pimascor-proxy.network' "${CADDY_QUADLET}" ||
  ! grep -Fq 'Volume=%h/bridge-ph/pimascor/web-dist:/srv/bridge-ph-pimascor:ro,Z' "${CADDY_QUADLET}"; then
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

# The shared Caddy Quadlet may retain a legacy site mount after that site was
# retired.  Remove only this known, absent path; never delete its host data.
stale_legacy_source='/home/jk/bridge-ph/accustanda-demo'
if [[ ! -e "${stale_legacy_source}" ]] &&
  grep -Eq "^Volume=${stale_legacy_source}:" "${CADDY_QUADLET}"; then
  quadlet_tmp="$(mktemp "${CADDY_QUADLET}.next.XXXXXX")"
  awk -v source="${stale_legacy_source}" '
    index($0, "Volume=" source ":") != 1 { print }
  ' "${CADDY_QUADLET}" > "${quadlet_tmp}"
  chmod 600 "${quadlet_tmp}"
  mv "${quadlet_tmp}" "${CADDY_QUADLET}"
  printf 'Removed stale Caddy bind mount for missing legacy path: %s\n' "${stale_legacy_source}"
fi

systemctl --user daemon-reload
systemctl --user restart bridge-ph-pimascor-proxy-network.service
systemctl --user restart caddy.service
podman exec caddy caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
curl --fail --silent --show-error --location --max-time 15 "https://delegateops.business/pimascor/" >/dev/null
printf '%s\n' 'Production Caddy route is active at https://delegateops.business/pimascor/'
