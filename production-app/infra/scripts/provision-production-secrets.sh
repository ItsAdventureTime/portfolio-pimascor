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

json_escape() {
  local value="$1"
  value=${value//\\/\\\\}
  value=${value//\"/\\\"}
  value=${value//$'\n'/\\n}
  value=${value//$'\r'/\\r}
  printf '%s' "$value"
}

prompt_account_field() {
  local label="$1"
  local default_value="$2"
  local value
  read -r -p "$label [$default_value]: " value
  value="${value:-$default_value}"
  printf '%s' "$value"
}

create_account_manifest() {
  local name=bridge_ph_pimascor_account_bootstrap
  if podman secret exists "$name"; then
    printf 'Keeping existing secret: %s\n' "$name"
    return 0
  fi

  printf '%s\n' 'Define the Section 1 production accounts. These fields contain metadata only; users choose passwords after email OTP activation.'
  local manifest='['
  local first=true business_role technical_role username email display_name
  append_account() {
    business_role="$1"
    technical_role="$2"
    username="$(prompt_account_field "${business_role} username" "$3")"
    email="$(prompt_account_field "${business_role} email" "$4")"
    display_name="$(prompt_account_field "${business_role} display name" "$5")"
    if [[ "$first" == true ]]; then first=false; else manifest+=','; fi
    manifest+="{\"business_role\":\"$(json_escape "$business_role")\",\"username\":\"$(json_escape "$username")\",\"email\":\"$(json_escape "$email")\",\"display_name\":\"$(json_escape "$display_name")\",\"role\":\"$technical_role\"}"
  }
  append_account 'Admin (Team)' ADMIN admin-team team@bridge-ph.com 'Bridge PH Team'
  append_account 'Admin (Alyssa)' ADMIN alyssa.d alyssa.d@bridge-ph.com 'Alyssa D.'
  append_account 'GM' GM carmel.urot carmel.urot@pimascor.com 'Carmel Urot'
  append_account 'DCS' DCS dan.c.subido dan.c.subido@gmail.com 'Dan C. Subido'
  append_account 'Sales (Maker) - Leane' REQUESTER leane.tejero leane.tejero@pimascor.com 'Leane Tejero'
  append_account 'Sales (Maker) - Romeo' REQUESTER romeo.reano romeo.reano@pimascor.com 'Romeo Reano'
  append_account 'Processor (Maker) - 1' REQUESTER processor1 processor1@pimascor 'Processor 1'
  append_account 'Processor (Maker) - 2' REQUESTER processor2 processor2@pimascor.com 'Processor 2'
  append_account 'Processor (Maker) - 3' REQUESTER processor3 processor3@pimascor.com 'Processor 3'
  append_account 'Bookkeeper (Mich)' MICH operations operations@pimascor.com 'Mich'
  manifest+=']'
  printf '%s' "$manifest" | podman secret create "$name" - >/dev/null
  unset manifest username email display_name business_role technical_role
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
create_account_manifest

printf '%s\n' 'Production secret provisioning complete. Run update-production.sh next.'
