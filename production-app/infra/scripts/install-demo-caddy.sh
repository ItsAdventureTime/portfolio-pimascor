#!/usr/bin/env bash
set -Eeuo pipefail

normalize_demo_quadlet() {
  local input="$1" output="$2"
  awk '
    /^Network=bridge-ph-pimascor-demo-proxy\.network$/ { next }
    /^Volume=[^:]*:\/srv\/bridge-ph-pimascor-demo(:|$)/ { next }
    /^\[Container\]$/ && !inserted {
      print
      print "Network=bridge-ph-pimascor-demo-proxy.network"
      print "Volume=%h/bridge-ph/pimascor-demo/web-dist:/srv/bridge-ph-pimascor-demo:ro,Z"
      inserted=1
      next
    }
    { print }
    END { if (!inserted) exit 3 }
  ' "${input}" >"${output}"
}

if [[ "${PIMASCOR_INSTALL_DEMO_CADDY_NORMALIZE_ONLY:-}" == 1 ]]; then
  [[ "$#" -eq 2 ]] || { printf '%s\n' 'Usage: PIMASCOR_INSTALL_DEMO_CADDY_NORMALIZE_ONLY=1 install-demo-caddy.sh INPUT OUTPUT' >&2; exit 2; }
  normalize_demo_quadlet "$1" "$2"
  exit 0
fi

# Install the reviewed demo route only after the complete edge configuration
# and the Caddy Quadlet validate from disposable staging files.
APP_ROOT="${HOME}/bridge-ph/pimascor-demo"
CADDY_CONF_ROOT="${PIMASCOR_CADDY_CONF_ROOT:-${HOME}/caddy/conf}"
CADDY_QUADLET="${PIMASCOR_CADDY_QUADLET:-${HOME}/.config/containers/systemd/caddy/caddy.container}"
SOURCE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CADDYFILE="${CADDY_CONF_ROOT}/Caddyfile"
HANDLERS="${CADDY_CONF_ROOT}/bridge-ph-pimascor-demo.Caddyfile"
SOURCE_HANDLERS="${PIMASCOR_DEMO_HANDLERS:-${SOURCE_ROOT}/infra/caddy/bridge-ph-pimascor-demo.Caddyfile}"
IMPORT='import /etc/caddy/bridge-ph-pimascor-demo.Caddyfile'
MARKER='# Managed by install-demo-caddy.sh: PIMASCOR demo handlers'
validation_root=""
quadlet_root=""
PODMAN_SYSTEM_GENERATOR="${PODMAN_SYSTEM_GENERATOR:-/usr/lib/systemd/system-generators/podman-system-generator}"

if [[ ! -f "${CADDYFILE}" ]]; then
  for candidate in "${HOME}/caddy/conf" "/home/jk/caddy/conf"; do
    if [[ -f "${candidate}/Caddyfile" ]]; then
      CADDY_CONF_ROOT="${candidate}"
      CADDYFILE="${candidate}/Caddyfile"
      HANDLERS="${candidate}/bridge-ph-pimascor-demo.Caddyfile"
      break
    fi
  done
fi

die() { printf '%s\n' "$*" >&2; exit 1; }
if [[ "${PIMASCOR_INSTALL_DEMO_CADDY_TEST_MODE:-}" != 1 ]]; then
  [[ "$(uname -s)" != Darwin ]] || die 'Run this on the Fedora CoreOS VPS.'
  [[ "${EUID}" -ne 0 ]] || die 'Refusing to run as root.'
fi
[[ -f "${CADDYFILE}" && -f "${CADDY_QUADLET}" ]] || die 'Shared Caddy configuration or Quadlet is missing.'
[[ -f "${SOURCE_HANDLERS}" ]] || die 'Committed demo Caddy fragment is missing.'
[[ -x "${PODMAN_SYSTEM_GENERATOR}" ]] || die "Podman system generator is unavailable: ${PODMAN_SYSTEM_GENERATOR}"
grep -Eq '^delegateops\.business[[:space:]]*\{' "${CADDYFILE}" || die 'Expected delegateops.business site block was not found; refusing to edit Caddy.'
[[ -d "${APP_ROOT}/web-dist" ]] || die "Demo web root not found: ${APP_ROOT}/web-dist"
if [[ "${PIMASCOR_INSTALL_DEMO_CADDY_TEST_MODE:-}" != 1 ]]; then
  systemctl --user show --property=LoadState --value caddy.service | grep -Fxq loaded || die 'Rootless caddy.service is unavailable.'
fi

# The running Quadlet is the source of truth for the validation image. Do not
# silently validate with a different tag than the service will run.
CADDY_IMAGE="$(awk -F= '/^Image=/{print $2; exit}' "${CADDY_QUADLET}")"
[[ "${CADDY_IMAGE}" == *@sha256:* ]] || die "Caddy Quadlet Image= must be digest-pinned: ${CADDY_IMAGE:-missing}"

cleanup() {
  [[ -z "${validation_root}" || ! -d "${validation_root}" ]] || rm -rf -- "${validation_root}"
  [[ -z "${quadlet_root}" || ! -d "${quadlet_root}" ]] || rm -rf -- "${quadlet_root}"
}
trap cleanup EXIT

validation_root="$(mktemp -d "${CADDY_CONF_ROOT}.validate.XXXXXX")"
quadlet_root="$(mktemp -d "${CADDY_QUADLET}.validate.XXXXXX")"
cp -a "${CADDY_CONF_ROOT}/." "${validation_root}/"
install -m 600 "${SOURCE_HANDLERS}" "${validation_root}/bridge-ph-pimascor-demo.Caddyfile"
install -m 600 "${CADDY_QUADLET}" "${quadlet_root}/caddy.container"
validation_caddyfile="${validation_root}/Caddyfile"
validation_handlers="${validation_root}/bridge-ph-pimascor-demo.Caddyfile"
validation_quadlet="${quadlet_root}/caddy.container"

# Adopt one canonical imported fragment, or insert it into the site block.
if grep -Eq '^[[:space:]]*import[[:space:]]+bridge-ph-pimascor-demo\.Caddyfile[[:space:]]*$' "${validation_caddyfile}"; then
  tmp="$(mktemp "${validation_caddyfile}.next.XXXXXX")"
  awk '!/^[[:space:]]*import[[:space:]]+bridge-ph-pimascor-demo\.Caddyfile[[:space:]]*$/ { print }' "${validation_caddyfile}" >"${tmp}"
  chmod 600 "${tmp}"; mv "${tmp}" "${validation_caddyfile}"
fi
if ! grep -Fq "${IMPORT}" "${validation_caddyfile}"; then
  tmp="$(mktemp "${validation_caddyfile}.next.XXXXXX")"
  awk -v marker="${MARKER}" -v import_line="${IMPORT}" '
    !inserted && /^delegateops\.business[[:space:]]*\{/ { print; print "\t" marker; print "\t" import_line; inserted=1; next }
    { print }
    END { if (!inserted) exit 3 }
  ' "${validation_caddyfile}" >"${tmp}"
  chmod 600 "${tmp}"; mv "${tmp}" "${validation_caddyfile}"
fi

grep -Fq "${IMPORT}" "${validation_caddyfile}" || die 'Demo Caddy import is absent; refusing to continue.'
grep -Fq 'bridge-ph-pimascor-demo-api:8000' "${validation_handlers}" || die 'Demo API upstream is absent; refusing to continue.'
grep -Fq '/srv/bridge-ph-pimascor-demo' "${validation_handlers}" || die 'Demo static root is absent; refusing to continue.'

# Quadlet keys belong in [Container]. Remove every prior demo-specific entry,
# including entries misplaced in [Service], then insert exactly one of each.
tmp="$(mktemp "${validation_quadlet}.next.XXXXXX")"
normalize_demo_quadlet "${validation_quadlet}" "${tmp}"
chmod 600 "${tmp}"; mv "${tmp}" "${validation_quadlet}"
[[ "$(grep -Ec '^Network=bridge-ph-pimascor-demo-proxy\.network$' "${validation_quadlet}")" -eq 1 ]] || die 'Demo network entry was not normalized.'
[[ "$(grep -Ec '^Volume=%h/bridge-ph/pimascor-demo/web-dist:/srv/bridge-ph-pimascor-demo:ro,Z$' "${validation_quadlet}")" -eq 1 ]] || die 'Demo web volume entry was not normalized.'

# Validate exactly what will be installed. A failed validation exits before
# any live file is touched.
podman run --rm --network none --volume "${validation_root}:/etc/caddy:ro,Z" "${CADDY_IMAGE}" caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
QUADLET_UNIT_DIRS="${quadlet_root}" "${PODMAN_SYSTEM_GENERATOR}" --user --dryrun >/dev/null

atomic_install() {
  local source="$1" target="$2" temp
  temp="$(mktemp "${target}.next.XXXXXX")"
  install -m 600 "${source}" "${temp}"
  mv -f "${temp}" "${target}"
}
atomic_install "${validation_caddyfile}" "${CADDYFILE}"
atomic_install "${validation_handlers}" "${HANDLERS}"
atomic_install "${validation_quadlet}" "${CADDY_QUADLET}"

systemctl --user daemon-reload
systemctl --user restart bridge-ph-pimascor-demo-proxy-network.service
systemctl --user restart caddy.service
podman exec caddy caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile

curl --fail --silent --show-error --head --location --max-time 15 https://delegateops.business/demo/pimascor | grep -Eq '^HTTP/[0-9.]+ 308([[:space:]]|$)'
curl --fail --silent --show-error --location --max-time 15 https://delegateops.business/demo/pimascor/ >/dev/null
api_health_url='https://delegateops.business/demo/pimascor/api/v1/health'
for _attempt in {1..30}; do
  if curl --fail --silent --show-error --location --max-time 10 "${api_health_url}" >/dev/null; then
    printf '%s\n' 'Demo Caddy redirect, route, and API health checks are active at https://delegateops.business/demo/pimascor/'
    exit 0
  fi
  sleep 2
done
die "Demo API did not become reachable through Caddy: ${api_health_url}"
