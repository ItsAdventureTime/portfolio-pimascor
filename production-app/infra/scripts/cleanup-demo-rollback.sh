#!/usr/bin/env bash
set -Eeuo pipefail

# Interactively remove every local PIMASCOR demo rollback after showing the
# exact targets and receiving one explicit confirmation. This script never
# touches the active deployment, PostgreSQL, secrets, Quadlets, or Backblaze.

APP_ROOT="${HOME}/bridge-ph/pimascor-demo"
IMAGE_REPOSITORY="localhost/bridge-ph-pimascor-demo-api"
RUNTIME_ROOT="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
MAINTENANCE_LOCK="${RUNTIME_ROOT}/bridge-ph-pimascor-demo-maintenance.lock"
LIST_ONLY=false
rollback_images=()
rollback_directories=()

usage() {
  printf '%s\n' \
    'Usage: infra/scripts/cleanup-demo-rollback.sh [--list]' \
    '' \
    'With no option, the script lists all local demo rollbacks, asks once,' \
    'and deletes them only if you answer y. --list never deletes anything.'
}

case "${1:-}" in
  '')
    ;;
  --list)
    (($# == 1)) || { usage >&2; exit 2; }
    LIST_ONLY=true
    ;;
  --help|-h)
    usage
    exit 0
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac

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

[[ "$(podman info --format '{{.Host.Security.Rootless}}')" == 'true' ]] || {
  printf '%s\n' 'Refusing to run: use the rootless Linux user that owns the PIMASCOR demo.' >&2
  exit 1
}

while IFS= read -r image_name; do
  if [[ "${image_name}" =~ ^localhost/bridge-ph-pimascor-demo-api:rollback-[0-9]{8}T[0-9]{6}Z$ ]]; then
    rollback_images+=("${image_name}")
  elif [[ "${image_name}" == "${IMAGE_REPOSITORY}:rollback-"* ]]; then
    printf 'Refusing cleanup: malformed rollback image name: %s\n' "${image_name}" >&2
    exit 1
  fi
done < <(podman image ls --format '{{.Repository}}:{{.Tag}}' | sort)

if [[ -d "${APP_ROOT}" && ! -L "${APP_ROOT}" ]]; then
  while IFS= read -r directory_name; do
    directory_base="$(basename -- "${directory_name}")"
    if [[ "${directory_base}" =~ ^web-dist\.previous\.[0-9]{8}T[0-9]{6}Z$ ]]; then
      rollback_directories+=("${directory_name}")
    else
      printf 'Refusing cleanup: malformed rollback directory name: %s\n' "${directory_name}" >&2
      exit 1
    fi
  done < <(find "${APP_ROOT}" -mindepth 1 -maxdepth 1 -type d -name 'web-dist.previous.*' -print | sort)
fi

printf '%s\n' 'Local PIMASCOR demo rollbacks selected for cleanup:'
printf '%s\n' 'API images:'
if ((${#rollback_images[@]})); then
  for image_name in "${rollback_images[@]}"; do
    image_size="$(podman image inspect --format '{{.Size}} bytes' "${image_name}")"
    printf '  %s (%s)\n' "${image_name}" "${image_size}"
  done
else
  printf '%s\n' '  (none)'
fi

printf '%s\n' 'Web directories:'
if ((${#rollback_directories[@]})); then
  for directory_name in "${rollback_directories[@]}"; do
    directory_size="$(du -sh -- "${directory_name}" | awk '{print $1}')"
    printf '  %s (%s)\n' "${directory_name}" "${directory_size}"
  done
else
  printf '%s\n' '  (none)'
fi

if ((${#rollback_images[@]} == 0 && ${#rollback_directories[@]} == 0)); then
  printf '%s\n' 'Nothing to delete.'
  exit 0
fi

if [[ "${LIST_ONLY}" == true ]]; then
  printf '%s\n' 'List only: nothing was deleted.'
  exit 0
fi

active_web="${APP_ROOT}/web-dist"
podman image exists "${IMAGE_REPOSITORY}:demo" || {
  printf '%s\n' 'Refusing cleanup: the active API image is missing.' >&2
  exit 1
}
systemctl --user is-active --quiet bridge-ph-pimascor-demo-api.service || {
  printf '%s\n' 'Refusing cleanup: the active API service is not running.' >&2
  exit 1
}
systemctl --user is-active --quiet caddy.service || {
  printf '%s\n' 'Refusing cleanup: Caddy is not running.' >&2
  exit 1
}
[[ "$(podman inspect --format '{{.State.Health.Status}}' bridge-ph-pimascor-demo-api)" == 'healthy' ]] || {
  printf '%s\n' 'Refusing cleanup: the active API container is not healthy.' >&2
  exit 1
}
[[ -f "${active_web}/index.html" && -f "${active_web}/manifest.webmanifest" && -f "${active_web}/sw.js" ]] || {
  printf '%s\n' 'Refusing cleanup: the active PWA build is incomplete.' >&2
  exit 1
}

resolved_app_root="$(realpath -e -- "${APP_ROOT}")"
for directory_name in "${rollback_directories[@]}"; do
  [[ -d "${directory_name}" && ! -L "${directory_name}" ]] || {
    printf 'Refusing cleanup: unexpected non-directory or symlink: %s\n' "${directory_name}" >&2
    exit 1
  }
  resolved_directory="$(realpath -e -- "${directory_name}")"
  [[ "$(dirname -- "${resolved_directory}")" == "${resolved_app_root}" ]] || {
    printf 'Refusing cleanup: rollback directory escaped its expected parent: %s\n' "${resolved_directory}" >&2
    exit 1
  }
  [[ "$(stat -c '%u' -- "${resolved_directory}")" == "$(id -u)" ]] || {
    printf 'Refusing cleanup: rollback directory is not owned by UID %s: %s\n' "$(id -u)" "${resolved_directory}" >&2
    exit 1
  }
  if mountpoint --quiet "${resolved_directory}"; then
    printf 'Refusing cleanup: rollback directory is a mount point: %s\n' "${resolved_directory}" >&2
    exit 1
  fi
done

printf '\nThis will permanently delete all %d API rollback image(s) and %d previous web build(s).\n' \
  "${#rollback_images[@]}" "${#rollback_directories[@]}"
printf '%s\n' 'This cleanup does not access Backblaze B2; the demo has no backup repository.'
read -r -p 'Are the targets above correct and should they all be deleted? [y/N] ' answer
case "${answer}" in
  y|Y|yes|YES|Yes)
    ;;
  *)
    printf '%s\n' 'Cleanup cancelled. Nothing was deleted.'
    exit 0
    ;;
esac

for image_name in "${rollback_images[@]}"; do
  # No --force: Podman must refuse if any container still uses the image.
  podman image rm --no-prune "${image_name}"
done

for directory_name in "${rollback_directories[@]}"; do
  rm --recursive --force --one-file-system --preserve-root=all -- "${directory_name}"
done

printf '\nCleanup completed. Removed %d API rollback image(s) and %d previous web build(s).\n' \
  "${#rollback_images[@]}" "${#rollback_directories[@]}"
printf '%s\n' 'No database, Quadlet, Podman secret, or Backblaze object was modified.'
