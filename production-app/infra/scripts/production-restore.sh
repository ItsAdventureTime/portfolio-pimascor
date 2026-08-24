#!/usr/bin/env bash
set -Eeuo pipefail

REPOSITORY="s3:https://s3.us-west-001.backblazeb2.com/bridge-ph/pimascor/backups/restic"
RESTORE_TARGET="${HOME}/bridge-ph/pimascor-restore-quarantine"
LIVE_ROOT=""

[[ "$(uname -s)" != "Darwin" ]] || { printf '%s\n' 'Run this on the Fedora CoreOS VPS.' >&2; exit 1; }
[[ "${EUID}" -ne 0 ]] || { printf '%s\n' 'Use the rootless jk account.' >&2; exit 1; }
command -v podman >/dev/null || { printf '%s\n' 'Missing podman.' >&2; exit 1; }

snapshot="latest"
execute=false
list_only=false
while (($#)); do
  case "$1" in
    --snapshot) [[ $# -ge 2 ]] || exit 2; snapshot="$2"; shift 2 ;;
    --target) [[ $# -ge 2 ]] || exit 2; RESTORE_TARGET="$2"; shift 2 ;;
    --execute) execute=true; shift ;;
    --list) list_only=true; shift ;;
    --dry-run) execute=false; shift ;;
    --help|-h)
      printf '%s\n' 'Usage: production-restore.sh [--list] [--snapshot ID] [--target DIR] [--dry-run|--execute]'
      printf '%s\n' 'Dry-run is the default. Execute restores into a quarantine directory only.'
      exit 0
      ;;
    *) printf 'Unknown option: %s\n' "$1" >&2; exit 2 ;;
  esac
done

secret_args=(
  --secret bridge_ph_pimascor_b2_key_id,type=env,target=AWS_ACCESS_KEY_ID
  --secret bridge_ph_pimascor_b2_application_key,type=env,target=AWS_SECRET_ACCESS_KEY
  --secret bridge_ph_pimascor_restic_password,target=restic_password,uid=0,gid=0,mode=0400
)
for secret_name in bridge_ph_pimascor_b2_key_id bridge_ph_pimascor_b2_application_key bridge_ph_pimascor_restic_password; do
  podman secret exists "${secret_name}" || { printf 'Missing production Podman secret: %s\n' "${secret_name}" >&2; exit 1; }
done

restic_args=(
  podman run --rm --network bridge-ph-pimascor-egress.network
  "${secret_args[@]}"
  -e AWS_DEFAULT_REGION=us-west-001
  -e "RESTIC_REPOSITORY=${REPOSITORY}"
  -e RESTIC_PASSWORD_FILE=/run/secrets/restic_password
  docker.io/restic/restic@sha256:08916bcda4a4435f9d9828ebb4e91bb7ada3d2c8a53699788930e0ae1bd4fa67
)

if "${list_only}"; then
  "${restic_args[@]}" snapshots --compact
  exit 0
fi

if ! "${execute}"; then
  printf 'DRY RUN: repository=%s snapshot=%s target=%s\n' "${REPOSITORY}" "${snapshot}" "${RESTORE_TARGET}"
  printf '%s\n' 'DRY RUN: no data was downloaded and no production service was stopped.'
  printf '%s\n' 'Review the snapshot list, then rerun with --execute and an approved target.'
  exit 0
fi

LIVE_ROOT="$(realpath -m "${HOME}/bridge-ph/pimascor")"
target_parent="$(realpath -m "$(dirname -- "${RESTORE_TARGET}")")"
target_name="$(basename -- "${RESTORE_TARGET}")"
target_canonical="${target_parent}/${target_name}"
[[ "${target_canonical}" != "${LIVE_ROOT}" && "${target_canonical}" != "${LIVE_ROOT}/"* ]] || {
  printf 'Refusing restore target inside live production root: %s\n' "${target_canonical}" >&2
  exit 1
}
[[ -d "${target_parent}" && ! -L "${RESTORE_TARGET}" && -d "${RESTORE_TARGET}" ]] || {
  printf '%s\n' 'Restore target must be a pre-created, non-symlink directory.' >&2
  exit 1
}
[[ -z "$(find "${RESTORE_TARGET}" -mindepth 1 -maxdepth 1 -print -quit)" ]] || {
  printf '%s\n' 'Restore target must be empty; refusing to mix restore contents with existing files.' >&2
  exit 1
}
"${restic_args[@]}" restore "${snapshot}" --target "${RESTORE_TARGET}"
printf 'Restore completed into quarantine: %s\n' "${RESTORE_TARGET}"
printf '%s\n' 'Review checksums and application data before any controlled cutover.'
