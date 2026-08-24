#!/usr/bin/env bash
set -Eeuo pipefail

APP_ROOT="${HOME}/bridge-ph/pimascor"
CADDY_CONF_ROOT="${PIMASCOR_CADDY_CONF_ROOT:-}"
CADDY_QUADLET="${PIMASCOR_CADDY_QUADLET:-${HOME}/.config/containers/systemd/caddy/caddy.container}"
SOURCE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CADDYFILE="${CADDY_CONF_ROOT}/Caddyfile"
HANDLERS="${CADDY_CONF_ROOT}/pimascor-production.handlers.Caddyfile"
IMPORT='import /etc/caddy/pimascor-production.handlers.Caddyfile'
MARKER='# Managed by install-production-caddy.sh: PIMASCOR production handlers'
CADDY_IMAGE=""
PINNED_CADDY_IMAGE=""
validation_root=""

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
systemctl --user show --property=LoadState --value caddy.service | grep -Fxq 'loaded' || {
  printf '%s\n' 'Rootless Caddy user unit is unavailable: caddy.service.' >&2
  printf 'Expected Quadlet: %s\n' "${CADDY_QUADLET}" >&2
  exit 1
}
CADDY_IMAGE="$(awk -F= '/^Image=/{print $2; exit}' "${CADDY_QUADLET}")"
[[ -n "${CADDY_IMAGE}" ]] || { printf '%s\n' 'Caddy image was not found in the shared Caddy Quadlet.' >&2; exit 1; }
if [[ "${CADDY_IMAGE}" == *@sha256:* ]]; then
  PINNED_CADDY_IMAGE="${CADDY_IMAGE}"
elif [[ "${CADDY_IMAGE}" == "docker.io/library/caddy:alpine" ]]; then
  PINNED_CADDY_IMAGE="docker.io/library/caddy@sha256:98eb57d882ccd5213d1688764db10c1ca2c58a1ca3a6717a3411ad798f7a423a"
else
  printf 'Caddy image must use the approved digest-pinned reference: %s\n' "${CADDY_IMAGE}" >&2
  exit 1
fi

install -d -m 700 "${CADDY_CONF_ROOT}"
validation_root="$(mktemp -d "${CADDY_CONF_ROOT}.validate.XXXXXX")"
cleanup_validation() { [[ -n "${validation_root}" && -d "${validation_root}" ]] && rm -rf -- "${validation_root}"; }
trap cleanup_validation EXIT
cp -a "${CADDY_CONF_ROOT}/." "${validation_root}/"
install -m 600 "${SOURCE_ROOT}/infra/caddy/pimascor-production.handlers.Caddyfile" "${validation_root}/pimascor-production.handlers.Caddyfile"
validation_caddyfile="${validation_root}/Caddyfile"
validation_handlers="${validation_root}/pimascor-production.handlers.Caddyfile"

# Keep one canonical import. A legacy relative import would load the same
# production handlers twice after the absolute import below is installed.
if grep -Eq '^[[:space:]]*import[[:space:]]+pimascor-production\.handlers\.Caddyfile[[:space:]]*$' "${validation_caddyfile}"; then
  caddy_tmp="$(mktemp "${validation_caddyfile}.next.XXXXXX")"
  awk '
    /^[[:space:]]*import[[:space:]]+pimascor-production\.handlers\.Caddyfile[[:space:]]*$/ { next }
    { print }
  ' "${validation_caddyfile}" > "${caddy_tmp}"
  chmod 600 "${caddy_tmp}"
  mv "${caddy_tmp}" "${validation_caddyfile}"
fi

# Adopt an existing absolute import, or add the marker and import together.
if ! grep -Fq "${MARKER}" "${validation_caddyfile}" ||
  ! grep -Eq '^[[:space:]]*import[[:space:]]+/etc/caddy/pimascor-production\.handlers\.Caddyfile[[:space:]]*$' "${validation_caddyfile}"; then
  caddy_tmp="$(mktemp "${validation_caddyfile}.next.XXXXXX")"
  awk -v import_line="${IMPORT}" -v marker="${MARKER}" '
    /^[[:space:]]*import[[:space:]]+\/etc\/caddy\/pimascor-production\.handlers\.Caddyfile[[:space:]]*$/ {
      if (import_seen++) next
      if (!marker_seen) print "\t" marker
      marker_seen=1
      print
      next
    }
    index($0, marker) { marker_seen=1 }
    !inserted && $0 ~ /^delegateops\.business[[:space:]]*\{/ {
      if (!marker_seen) print "\t" marker
      if (!import_seen) print "\t" import_line
      marker_seen=1
      import_seen=1
      inserted=1
      print
      next
    }
    { print }
    END { if (!import_seen) exit 3 }
  ' "${validation_caddyfile}" > "${caddy_tmp}"
  chmod 600 "${caddy_tmp}"
  mv "${caddy_tmp}" "${validation_caddyfile}"
fi

if ! grep -Fq "${MARKER}" "${validation_caddyfile}"; then
  caddy_tmp="$(mktemp "${validation_caddyfile}.next.XXXXXX")"
  awk -v marker="${MARKER}" '
    !inserted && $0 ~ /^delegateops\.business[[:space:]]*\{/ {
      print
      print "    " marker
      inserted=1
      next
    }
    { print }
    END { if (!inserted) exit 3 }
  ' "${validation_caddyfile}" > "${caddy_tmp}"
  chmod 600 "${caddy_tmp}"
  mv "${caddy_tmp}" "${validation_caddyfile}"
fi

# caddy fmt makes only presentation changes; caddy validate catches syntax and
# provisioning errors before the shared edge service is restarted. Both run in
# disposable containers so no tooling is installed on the Fedora CoreOS host.
podman run --rm --network none \
  --volume "${validation_root}:/etc/caddy:Z" \
  "${PINNED_CADDY_IMAGE}" \
  caddy fmt --overwrite /etc/caddy/Caddyfile
podman run --rm --network none \
  --volume "${validation_root}:/etc/caddy:ro,Z" \
  "${PINNED_CADDY_IMAGE}" \
  caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile

# Install the fully validated pair only after the disposable complete config
# passes. The live/shared configuration remains untouched on validation error.
install -m 600 "${validation_caddyfile}" "${CADDYFILE}"
install -m 600 "${validation_handlers}" "${HANDLERS}"

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

if [[ "${CADDY_IMAGE}" != *@sha256:* ]]; then
  quadlet_tmp="$(mktemp "${CADDY_QUADLET}.next.XXXXXX")"
  awk -v pinned="${PINNED_CADDY_IMAGE}" '
    /^Image=/ { print "Image=" pinned; next }
    { print }
  ' "${CADDY_QUADLET}" > "${quadlet_tmp}"
  chmod 600 "${quadlet_tmp}"
  mv "${quadlet_tmp}" "${CADDY_QUADLET}"
  printf 'Pinned the shared Caddy Quadlet to %s.\n' "${PINNED_CADDY_IMAGE}"
fi

systemctl --user daemon-reload
systemctl --user restart bridge-ph-pimascor-proxy-network.service
systemctl --user restart caddy.service
podman exec caddy caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
curl --fail --silent --show-error --location --max-time 15 "https://delegateops.business/prod/pimascor/" >/dev/null

api_health_url='https://delegateops.business/prod/pimascor/api/v1/health'
api_ready=false
printf 'Waiting for production API health through Caddy...\n'
for _attempt in {1..30}; do
  if curl --fail --silent --location --max-time 10 "${api_health_url}" >/dev/null 2>&1; then
    api_ready=true
    break
  fi
  sleep 2
done
if [[ "${api_ready}" != true ]]; then
  printf 'Production API did not become reachable through Caddy: %s\n' "${api_health_url}" >&2
  systemctl --user status --no-pager --full bridge-ph-pimascor-api.service >&2 || true
  exit 1
fi
printf '%s\n' 'Production Caddy route and API health check are active at https://delegateops.business/prod/pimascor/'
