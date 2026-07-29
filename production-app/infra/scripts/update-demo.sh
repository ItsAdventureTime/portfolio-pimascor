#!/usr/bin/env bash
set -Eeuo pipefail

# Guarded update helper for an already-installed PIMASCOR demo. It deliberately
# does not create/replace secrets, modify Caddy configuration, publish ports, or
# update unrelated containers.

APP_ROOT="${HOME}/bridge-ph/pimascor-demo"
QUADLET_ROOT="${HOME}/.config/containers/systemd/bridge-ph/pimascor-demo"
TIMER_ROOT="${HOME}/.config/systemd/user"
PUBLIC_URL="https://delegateops.business/pimascor/demo/"
API_HEALTH_URL="https://delegateops.business/pimascor/demo/api/v1/health"
SOURCE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RESET_BASELINE=true
RUNTIME_ROOT="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
MAINTENANCE_LOCK="${RUNTIME_ROOT}/bridge-ph-pimascor-demo-maintenance.lock"

[[ "${EUID}" -ne 0 ]] || {
  printf '%s\n' 'Refusing to run as root: use the rootless Linux user that owns the PIMASCOR demo.' >&2
  exit 1
}
command -v flock >/dev/null || {
  printf '%s\n' 'Missing required command: flock' >&2
  exit 1
}
exec 9>"${MAINTENANCE_LOCK}"
flock --nonblock 9 || {
  printf '%s\n' 'Another PIMASCOR demo update or cleanup operation is already running.' >&2
  exit 1
}

usage() {
  printf '%s\n' \
    'Usage: infra/scripts/update-demo.sh [--source PATH] [--keep-demo-data]' \
    '' \
    '  --source PATH       production-app source root (default: inferred from this script)' \
    '  --keep-demo-data    migrate existing demo records but do not reload the baseline'
}

while (($#)); do
  case "$1" in
    --source)
      [[ $# -ge 2 ]] || { usage; exit 2; }
      SOURCE_ROOT="$(cd "$2" && pwd)"
      shift 2
      ;;
    --keep-demo-data)
      RESET_BASELINE=false
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown option: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

required_files=(
  "${SOURCE_ROOT}/apps/api/Containerfile"
  "${SOURCE_ROOT}/apps/api/migrations/versions/20260723_0005_finance_controls.py"
  "${SOURCE_ROOT}/apps/api/migrations/versions/20260723_0006_document_storage.py"
  "${SOURCE_ROOT}/apps/api/migrations/versions/20260723_0007_incident_reporting.py"
  "${SOURCE_ROOT}/apps/api/migrations/versions/20260723_0008_profitability_billing_controls.py"
  "${SOURCE_ROOT}/apps/api/src/pimascor_api/incident_admin.py"
  "${SOURCE_ROOT}/apps/web/Containerfile"
  "${SOURCE_ROOT}/infra/quadlet/demo/bridge-ph-pimascor-demo-api.container"
  "${SOURCE_ROOT}/infra/quadlet/demo/bridge-ph-pimascor-demo-db.container"
  "${SOURCE_ROOT}/infra/quadlet/demo/bridge-ph-pimascor-demo-reset.container"
  "${SOURCE_ROOT}/infra/quadlet/demo/bridge-ph-pimascor-demo-data.network"
  "${SOURCE_ROOT}/infra/quadlet/demo/bridge-ph-pimascor-demo-egress.network"
  "${SOURCE_ROOT}/infra/quadlet/demo/bridge-ph-pimascor-demo-proxy.network"
  "${SOURCE_ROOT}/infra/systemd/bridge-ph-pimascor-demo-reset.timer"
)

for required_file in "${required_files[@]}"; do
  [[ -f "${required_file}" ]] || { printf 'Missing required file: %s\n' "${required_file}" >&2; exit 1; }
done

db_quadlet="${SOURCE_ROOT}/infra/quadlet/demo/bridge-ph-pimascor-demo-db.container"
api_quadlet="${SOURCE_ROOT}/infra/quadlet/demo/bridge-ph-pimascor-demo-api.container"
reset_quadlet="${SOURCE_ROOT}/infra/quadlet/demo/bridge-ph-pimascor-demo-reset.container"
grep -Fqx 'Volume=%h/bridge-ph/pimascor-demo/data/postgres/18/docker:/var/lib/postgresql/18/docker:U,Z' "${db_quadlet}" || {
  printf 'Refusing to update: the PostgreSQL Quadlet does not use the required direct PostgreSQL 18 PGDATA mount.\n' >&2
  exit 1
}
grep -Fqx 'Environment=PGDATA=/var/lib/postgresql/18/docker' "${db_quadlet}" || {
  printf 'Refusing to update: the PostgreSQL Quadlet does not declare the required PostgreSQL 18 PGDATA path.\n' >&2
  exit 1
}
grep -Fqx 'Volume=%h/bridge-ph/pimascor-demo/data/uploads-tmp:/tmp:U,Z' "${api_quadlet}" || {
  printf 'Refusing to update: the API Quadlet does not provide the required private upload spool for 100 MB documents.\n' >&2
  exit 1
}
grep -Fqx 'Environment=APP_ENV=maintenance' "${reset_quadlet}" || {
  printf 'Refusing to update: the reset Quadlet must use the restricted maintenance runtime.\n' >&2
  exit 1
}
grep -Fq 'Literal["development", "test", "maintenance", "production"]' \
  "${SOURCE_ROOT}/apps/api/src/pimascor_api/config.py" || {
  printf 'Refusing to update: the API configuration does not define the maintenance runtime.\n' >&2
  exit 1
}
grep -Fq 'revision: str = "20260723_0005"' "${SOURCE_ROOT}/apps/api/migrations/versions/20260723_0005_finance_controls.py" || {
  printf 'Refusing to update: the finance-controls database migration is missing or has an unexpected revision ID.\n' >&2
  exit 1
}
grep -Fq 'revision: str = "20260723_0006"' "${SOURCE_ROOT}/apps/api/migrations/versions/20260723_0006_document_storage.py" || {
  printf 'Refusing to update: the document-storage database migration is missing or has an unexpected revision ID.\n' >&2
  exit 1
}
grep -Fq 'revision: str = "20260723_0007"' "${SOURCE_ROOT}/apps/api/migrations/versions/20260723_0007_incident_reporting.py" || {
  printf 'Refusing to update: the incident-reporting database migration is missing or has an unexpected revision ID.\n' >&2
  exit 1
}
grep -Fq 'revision: str = "20260723_0008"' "${SOURCE_ROOT}/apps/api/migrations/versions/20260723_0008_profitability_billing_controls.py" || {
  printf 'Refusing to update: the profitability and Billing-control migration is missing or has an unexpected revision ID.\n' >&2
  exit 1
}
grep -Fqx 'Environment=INCIDENT_ADMIN_EMAIL=alyssa.d@bridge-ph.com' "${api_quadlet}" || {
  printf 'Refusing to update: the reviewed Bridge PH incident recipient is missing from the API Quadlet.\n' >&2
  exit 1
}
grep -Fqx 'Environment=INCIDENT_DEVELOPER_EMAIL=jk@delegateops.business' "${api_quadlet}" || {
  printf 'Refusing to update: the reviewed Developer incident recipient is missing from the API Quadlet.\n' >&2
  exit 1
}
[[ "$(podman info --format '{{.Host.Security.Rootless}}')" == 'true' ]] || {
  printf 'Refusing to run: use the rootless Linux user that owns the PIMASCOR and Caddy services.\n' >&2
  exit 1
}

for secret_name in \
  bridge_ph_pimascor_demo_postgres_password \
  bridge_ph_pimascor_demo_database_url \
  bridge_ph_pimascor_demo_resend_api_key \
  bridge_ph_pimascor_demo_b2_key_id \
  bridge_ph_pimascor_demo_b2_application_key; do
  podman secret exists "${secret_name}" || { printf 'Missing Podman secret: %s\n' "${secret_name}" >&2; exit 1; }
done

install -d -m 700 \
  "${APP_ROOT}" \
  "${APP_ROOT}/data/postgres/18/docker" \
  "${APP_ROOT}/data/uploads-tmp" \
  "${QUADLET_ROOT}" \
  "${TIMER_ROOT}"

printf 'Retiring obsolete demo backup units; production backup templates are untouched...\n'
systemctl --user disable --now \
  bridge-ph-pimascor-demo-backup.timer \
  bridge-ph-pimascor-demo-backup-retention.timer \
  >/dev/null 2>&1 || true
systemctl --user stop \
  bridge-ph-pimascor-demo-backup.service \
  bridge-ph-pimascor-demo-backup-retention.service \
  bridge-ph-pimascor-demo-db-dump.service \
  >/dev/null 2>&1 || true
rm -f -- \
  "${QUADLET_ROOT}/bridge-ph-pimascor-demo-db-dump.container" \
  "${QUADLET_ROOT}/bridge-ph-pimascor-demo-backup.container" \
  "${QUADLET_ROOT}/bridge-ph-pimascor-demo-backup-retention.container" \
  "${TIMER_ROOT}/bridge-ph-pimascor-demo-backup.timer" \
  "${TIMER_ROOT}/bridge-ph-pimascor-demo-backup-retention.timer"

printf 'Installing and validating reviewed Quadlet and timer definitions...\n'
quadlet_files=(
  "${SOURCE_ROOT}/infra/quadlet/demo/bridge-ph-pimascor-demo-data.network"
  "${SOURCE_ROOT}/infra/quadlet/demo/bridge-ph-pimascor-demo-egress.network"
  "${SOURCE_ROOT}/infra/quadlet/demo/bridge-ph-pimascor-demo-proxy.network"
  "${SOURCE_ROOT}/infra/quadlet/demo/bridge-ph-pimascor-demo-db.container"
  "${SOURCE_ROOT}/infra/quadlet/demo/bridge-ph-pimascor-demo-api.container"
  "${SOURCE_ROOT}/infra/quadlet/demo/bridge-ph-pimascor-demo-reset.container"
)
for quadlet_file in "${quadlet_files[@]}"; do
  install -m 600 "${quadlet_file}" "${QUADLET_ROOT}/"
done
install -m 600 \
  "${SOURCE_ROOT}/infra/systemd/bridge-ph-pimascor-demo-reset.timer" \
  "${TIMER_ROOT}/"

systemctl --user daemon-reload
systemd-analyze --user --generators=true verify \
  bridge-ph-pimascor-demo-db.service \
  bridge-ph-pimascor-demo-api.service \
  bridge-ph-pimascor-demo-reset.service \
  bridge-ph-pimascor-demo-reset.timer

dependency_units=(
  bridge-ph-pimascor-demo-egress-network.service
  bridge-ph-pimascor-demo-proxy-network.service
  bridge-ph-pimascor-demo-data-network.service
)

printf 'Starting the private application networks and checking PostgreSQL...\n'
systemctl --user reset-failed \
  "${dependency_units[@]}" \
  bridge-ph-pimascor-demo-db.service \
  bridge-ph-pimascor-demo-api.service \
  bridge-ph-pimascor-demo-reset.service
systemctl --user start "${dependency_units[@]}"

if ! systemctl --user is-active --quiet bridge-ph-pimascor-demo-db.service; then
  if ! systemctl --user start bridge-ph-pimascor-demo-db.service; then
    printf 'PostgreSQL failed before the build phase. Status and recent logs follow:\n' >&2
    systemctl --user status bridge-ph-pimascor-demo-data-network.service bridge-ph-pimascor-demo-db.service --no-pager -l >&2 || true
    journalctl --user -u bridge-ph-pimascor-demo-db.service -n 120 --no-pager -o cat >&2 || true
    exit 1
  fi
fi

release_stamp="$(date -u +%Y%m%dT%H%M%SZ)"
rollback_image="localhost/bridge-ph-pimascor-demo-api:rollback-${release_stamp}"
rollback_image_created=false
if podman image exists localhost/bridge-ph-pimascor-demo-api:demo; then
  podman tag localhost/bridge-ph-pimascor-demo-api:demo "${rollback_image}"
  rollback_image_created=true
fi

printf 'Building the revised API image...\n'
podman build --pull=always --tag localhost/bridge-ph-pimascor-demo-api:demo "${SOURCE_ROOT}/apps/api"

web_stage="$(mktemp -d "${APP_ROOT}/web-dist.next.XXXXXX")"
printf 'Building the revised static PWA into staging...\n'
podman build \
  --pull=always \
  --output "type=local,dest=${web_stage}" \
  --build-arg VITE_BASE_PATH=/pimascor/demo/ \
  --build-arg VITE_API_URL=/pimascor/demo/api/v1 \
  --build-arg VITE_CSRF_COOKIE_NAME=bridge_ph_pimascor_demo_csrf \
  "${SOURCE_ROOT}/apps/web"

test -f "${web_stage}/index.html"
test -f "${web_stage}/manifest.webmanifest"
test -f "${web_stage}/sw.js"

previous_web="${APP_ROOT}/web-dist.previous.${release_stamp}"
if [[ -d "${APP_ROOT}/web-dist" ]]; then
  mv "${APP_ROOT}/web-dist" "${previous_web}"
fi
mv "${web_stage}" "${APP_ROOT}/web-dist"

if [[ "${RESET_BASELINE}" == true ]]; then
  printf 'Applying migrations and reloading the approved synthetic demo baseline...\n'
  api_action=(start bridge-ph-pimascor-demo-reset.service)
else
  printf 'Restarting the API so its entrypoint applies the forward migration...\n'
  api_action=(restart bridge-ph-pimascor-demo-api.service)
fi
if ! systemctl --user "${api_action[@]}"; then
  printf 'Application activation failed. Dependency status follows:\n' >&2
  systemctl --user status \
    "${dependency_units[@]}" \
    bridge-ph-pimascor-demo-db.service \
    bridge-ph-pimascor-demo-api.service \
    bridge-ph-pimascor-demo-reset.service \
    --no-pager -l >&2 || true
  printf 'Recent dependency logs follow:\n' >&2
  journalctl --user \
    -u bridge-ph-pimascor-demo-data-network.service \
    -u bridge-ph-pimascor-demo-db.service \
    -u bridge-ph-pimascor-demo-api.service \
    -u bridge-ph-pimascor-demo-reset.service \
    -n 120 --no-pager -o cat >&2 || true
  exit 1
fi

if [[ "${RESET_BASELINE}" == true ]]; then
  # The reset one-shot restarts the API without blocking in ExecStopPost. Wait
  # here for its health-gated systemd start job before probing the public route.
  systemctl --user start bridge-ph-pimascor-demo-api.service
fi

podman exec caddy caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
systemctl --user restart caddy.service

curl --fail --show-error "${API_HEALTH_URL}"
curl --fail --show-error --output /dev/null "${PUBLIC_URL}"

printf '\nUpdate completed.\n'
if [[ "${rollback_image_created}" == true ]]; then
  printf 'Rollback API image: %s\n' "${rollback_image}"
fi
if [[ -d "${previous_web}" ]]; then
  printf 'Rollback web directory: %s\n' "${previous_web}"
fi
printf 'Keep local rollback material until all five role walkthroughs pass.\n'
