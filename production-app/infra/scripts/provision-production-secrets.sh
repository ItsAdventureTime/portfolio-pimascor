#!/usr/bin/env bash
set -Eeuo pipefail

[[ "$(uname -s)" != "Darwin" ]] || { printf '%s\n' 'Run this on the Fedora CoreOS VPS.' >&2; exit 1; }
[[ "${EUID}" -ne 0 ]] || { printf '%s\n' 'Refusing to run as root; use rootless user jk.' >&2; exit 1; }
command -v podman >/dev/null || { printf '%s\n' 'Missing required command: podman' >&2; exit 1; }
[[ "$(podman info --format '{{.Host.Security.Rootless}}')" == 'true' ]] || {
  printf '%s\n' 'Rootless Podman is required.' >&2
  exit 1
}

create_secret() {
  local name="$1"
  local prompt="$2"
  local value

  if podman secret exists "$name"; then
    printf 'Keeping existing secret: %s\n' "$name"
    return 0
  fi

  while :; do
    read -r -s -p "$prompt: " value
    printf '\n'
    [[ -n "$value" ]] && break
    printf 'A non-empty value is required.\n' >&2
  done
  printf '%s' "$value" | podman secret create "$name" - >/dev/null
  unset value
  printf 'Created secret: %s\n' "$name"
}

printf '%s\n' 'Creating missing production secrets as rootless Podman secrets.'
printf '%s\n' 'Values are read interactively and are never written to this repository.'
printf '%s\n' 'The database URL password must match the PostgreSQL password.'

create_secret bridge_ph_pimascor_postgres_password 'PostgreSQL password'
create_secret bridge_ph_pimascor_database_url 'Database URL (for example postgresql+psycopg://pimascor:PASSWORD@database:5432/pimascor)'
create_secret bridge_ph_pimascor_resend_api_key 'Resend API key'
create_secret bridge_ph_pimascor_b2_key_id 'Backblaze B2 key ID'
create_secret bridge_ph_pimascor_b2_application_key 'Backblaze B2 application key'
create_secret bridge_ph_pimascor_pgpass 'PostgreSQL client password file line (database:5432:pimascor:pimascor:PASSWORD)'
create_secret bridge_ph_pimascor_restic_password 'Restic repository password'

printf '%s\n' 'Production secret provisioning complete. Run update-production.sh next.'
