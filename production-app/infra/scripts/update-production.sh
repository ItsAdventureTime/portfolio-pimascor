#!/usr/bin/env bash
set -Eeuo pipefail

APP_ROOT="${HOME}/bridge-ph/pimascor"
WEB_ROOT="${APP_ROOT}"
QUADLET_ROOT="${HOME}/.config/containers/systemd/bridge-ph/pimascor"
TIMER_ROOT="${HOME}/.config/systemd/user"
PUBLIC_URL="https://delegateops.business/pimascor/"
API_HEALTH_URL="https://delegateops.business/pimascor/api/v1/health"
SOURCE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME_ROOT="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
MAINTENANCE_LOCK="${RUNTIME_ROOT}/bridge-ph-pimascor-maintenance.lock"

[[ "$(uname -s)" != "Darwin" ]] || { printf '%s\n' 'Run this on the Fedora CoreOS VPS.' >&2; exit 1; }
[[ "${EUID}" -ne 0 ]] || { printf '%s\n' 'Refusing to run as root; use rootless user jk.' >&2; exit 1; }
command -v flock >/dev/null || { printf '%s\n' 'Missing required command: flock' >&2; exit 1; }
exec 9>"${MAINTENANCE_LOCK}"
flock --nonblock 9 || { printf '%s\n' 'Another production update is running.' >&2; exit 1; }

while (($#)); do
  case "$1" in
    --source) [[ $# -ge 2 ]] || exit 2; SOURCE_ROOT="$(cd "$2" && pwd)"; shift 2 ;;
    --help|-h) printf '%s\n' 'Usage: update-production.sh [--source PATH]'; exit 0 ;;
    *) printf 'Unknown option: %s\n' "$1" >&2; exit 2 ;;
  esac
done

required_files=(
  "${SOURCE_ROOT}/.deployment-source-commit"
  "${SOURCE_ROOT}/apps/api/Containerfile"
  "${SOURCE_ROOT}/apps/api/migrations/versions/20260729_0011_data_exports.py"
  "${SOURCE_ROOT}/apps/api/migrations/versions/20260801_0012_account_activation.py"
  "${SOURCE_ROOT}/apps/web/Containerfile"
  "${SOURCE_ROOT}/infra/quadlet/production/bridge-ph-pimascor-api.container"
  "${SOURCE_ROOT}/infra/quadlet/production/bridge-ph-pimascor-account-bootstrap.container"
  "${SOURCE_ROOT}/infra/quadlet/production/bridge-ph-pimascor-db.container"
  "${SOURCE_ROOT}/infra/quadlet/production/bridge-ph-pimascor-export-worker.container"
  "${SOURCE_ROOT}/infra/quadlet/production/bridge-ph-pimascor-data.network"
  "${SOURCE_ROOT}/infra/quadlet/production/bridge-ph-pimascor-egress.network"
  "${SOURCE_ROOT}/infra/quadlet/production/bridge-ph-pimascor-proxy.network"
)
for required_file in "${required_files[@]}"; do
  [[ -f "$required_file" ]] || { printf 'Missing required file: %s\n' "$required_file" >&2; exit 1; }
done
release_commit="$(tr -d '\r\n' < "${SOURCE_ROOT}/.deployment-source-commit")"
[[ "$release_commit" =~ ^[0-9a-f]{40}$ ]] || { printf '%s\n' 'Invalid Git commit marker.' >&2; exit 1; }
grep -Fqx 'Environment=DEPLOYMENT_TIER=production' "${SOURCE_ROOT}/infra/quadlet/production/bridge-ph-pimascor-api.container"
grep -Fqx 'Environment=DATA_EXPORT_ENABLED=true' "${SOURCE_ROOT}/infra/quadlet/production/bridge-ph-pimascor-api.container"
[[ "$(podman info --format '{{.Host.Security.Rootless}}')" == 'true' ]] || { printf '%s\n' 'Rootless Podman is required.' >&2; exit 1; }

for secret_name in bridge_ph_pimascor_postgres_password bridge_ph_pimascor_database_url bridge_ph_pimascor_resend_api_key bridge_ph_pimascor_b2_key_id bridge_ph_pimascor_b2_application_key bridge_ph_pimascor_pgpass bridge_ph_pimascor_restic_password bridge_ph_pimascor_account_bootstrap; do
  podman secret exists "$secret_name" || { printf 'Missing production Podman secret: %s\n' "$secret_name" >&2; exit 1; }
done

install -d -m 700 "$APP_ROOT" "$APP_ROOT/data/postgres/18/docker" "$APP_ROOT/data/uploads-tmp" "$APP_ROOT/backup-staging" "$APP_ROOT/restic-cache" "$QUADLET_ROOT" "$TIMER_ROOT"
quadlet_files=(bridge-ph-pimascor-data.network bridge-ph-pimascor-egress.network bridge-ph-pimascor-proxy.network bridge-ph-pimascor-db.container bridge-ph-pimascor-api.container bridge-ph-pimascor-account-bootstrap.container bridge-ph-pimascor-export-worker.container bridge-ph-pimascor-db-dump.container bridge-ph-pimascor-backup.container bridge-ph-pimascor-backup-retention.container)
for quadlet_file in "${quadlet_files[@]}"; do
  install -m 600 "${SOURCE_ROOT}/infra/quadlet/production/${quadlet_file}" "${QUADLET_ROOT}/${quadlet_file}"
done
install -m 600 "${SOURCE_ROOT}/infra/systemd/bridge-ph-pimascor-backup.timer" "${TIMER_ROOT}/bridge-ph-pimascor-backup.timer"
install -m 600 "${SOURCE_ROOT}/infra/systemd/bridge-ph-pimascor-backup-retention.timer" "${TIMER_ROOT}/bridge-ph-pimascor-backup-retention.timer"

systemctl --user daemon-reload
systemd-analyze --user --generators=true verify bridge-ph-pimascor-db.service bridge-ph-pimascor-account-bootstrap.service bridge-ph-pimascor-api.service bridge-ph-pimascor-export-worker.service bridge-ph-pimascor-db-dump.service bridge-ph-pimascor-backup.service
systemctl --user start bridge-ph-pimascor-data-network.service bridge-ph-pimascor-egress-network.service bridge-ph-pimascor-proxy-network.service
if ! systemctl --user start bridge-ph-pimascor-db.service; then
  printf '%s\n' 'PostgreSQL failed to start. Safe diagnostics follow; secret contents are not printed.' >&2
  systemctl --user status --no-pager --full bridge-ph-pimascor-db.service >&2 || true
  journalctl --user --unit=bridge-ph-pimascor-db.service --no-pager --lines=120 >&2 || true
  podman logs --tail=120 bridge-ph-pimascor-db >&2 || true
  exit 1
fi

printf 'Building production API image for commit %s...\n' "$release_commit"
podman build --pull=always --tag localhost/bridge-ph-pimascor-api:production "${SOURCE_ROOT}/apps/api"
web_stage="$(mktemp -d "${WEB_ROOT}/web-dist.next.XXXXXX")"
trap 'rm -rf -- "${web_stage}"' EXIT
podman build --pull=always --output "type=local,dest=${web_stage}" --build-arg VITE_BASE_PATH=/pimascor/ --build-arg VITE_API_URL=/pimascor/api/v1 --build-arg VITE_CSRF_COOKIE_NAME=bridge_ph_pimascor_csrf "${SOURCE_ROOT}/apps/web"
test -f "${web_stage}/index.html" && test -f "${web_stage}/manifest.webmanifest" && test -f "${web_stage}/sw.js"
install -d -m 700 "${WEB_ROOT}/web-dist"
find "${WEB_ROOT}/web-dist" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
cp -a "${web_stage}/." "${WEB_ROOT}/web-dist/"
rm -rf -- "${web_stage}"
trap - EXIT

systemctl --user restart bridge-ph-pimascor-account-bootstrap.service
systemctl --user restart bridge-ph-pimascor-api.service
systemctl --user restart bridge-ph-pimascor-export-worker.service
systemctl --user is-active --quiet bridge-ph-pimascor-api.service
systemctl --user is-active --quiet bridge-ph-pimascor-export-worker.service
systemctl --user enable --now bridge-ph-pimascor-backup.timer bridge-ph-pimascor-backup-retention.timer
printf 'Production release %s is active. Caddy remains unchanged; run install-production-caddy.sh after its preflight.\n' "$release_commit"
printf 'Expected public URL: %s\n' "$PUBLIC_URL"
printf 'Health check: %s\n' "$API_HEALTH_URL"
