#!/usr/bin/env bash
set -Eeuo pipefail

[[ "$(uname -s)" != "Darwin" ]] || { printf '%s\n' 'Run this on the Fedora CoreOS VPS.' >&2; exit 1; }
[[ "${EUID}" -ne 0 ]] || { printf '%s\n' 'Refusing to run as root; use rootless user jk.' >&2; exit 1; }
command -v podman >/dev/null || { printf '%s\n' 'Missing required command: podman' >&2; exit 1; }
[[ "$(podman info --format '{{.Host.Security.Rootless}}')" == 'true' ]] || { printf '%s\n' 'Rootless Podman is required.' >&2; exit 1; }

REPLACE_ACCOUNT_MANIFEST=false
INTERACTIVE_ACCOUNT_MANIFEST=false
while (($#)); do
  case "$1" in
    --replace-account-manifest) REPLACE_ACCOUNT_MANIFEST=true; shift ;;
    --interactive-account-manifest) INTERACTIVE_ACCOUNT_MANIFEST=true; shift ;;
    --help|-h) printf '%s\n' 'Usage: provision-production-secrets.sh [--replace-account-manifest] [--interactive-account-manifest]'; exit 0 ;;
    *) printf 'Unknown option: %s\n' "$1" >&2; exit 2 ;;
  esac
done

create_secret() {
  local name="$1" prompt="$2" value
  if podman secret exists "$name"; then printf 'Keeping existing secret: %s\n' "$name"; return 0; fi
  while :; do
    read -r -s -p "$prompt: " value; printf '\n'
    [[ -n "$value" ]] && break
    printf 'A non-empty value is required.\n' >&2
  done
  printf '%s' "$value" | podman secret create "$name" - >/dev/null
  unset value
  printf 'Created secret: %s\n' "$name"
}

read_secret_value() { local name="$1"; podman secret inspect --showsecret --format '{{.SecretData}}' "$name" 2>/dev/null; }
create_derived_secret() {
  local name="$1" value="$2"
  if podman secret exists "$name"; then printf 'Keeping existing secret: %s\n' "$name"; return 0; fi
  printf '%s' "$value" | podman secret create "$name" - >/dev/null
  printf 'Created derived secret: %s\n' "$name"
}
json_escape() {
  local value="$1"; value=${value//\\/\\\\}; value=${value//"/\\"}; value=${value//$'\n'/\\n}; value=${value//$'\r'/\\r}; printf '%s' "$value"
}
url_encode() {
  local value="$1" output='' char encoded index; LC_ALL=C
  for ((index = 0; index < ${#value}; index++)); do
    char="${value:index:1}"
    case "$char" in [a-zA-Z0-9.~_-]) output+="$char" ;; *) printf -v encoded '%%%02X' "'$char"; output+="$encoded" ;; esac
  done
  printf '%s' "$output"
}
pgpass_escape() { local value="$1"; value=${value//\\/\\\\}; value=${value//:/\\:}; printf '%s' "$value"; }
prompt_account_field() { local label="$1" default_value="$2" value; read -r -p "$label [$default_value]: " value; value="${value:-$default_value}"; printf '%s' "$value"; }

create_account_manifest() {
  local name=bridge_ph_pimascor_account_bootstrap
  if podman secret exists "$name" && [[ "$REPLACE_ACCOUNT_MANIFEST" != true ]]; then printf 'Keeping existing secret: %s\n' "$name"; return 0; fi
  printf '%s\n' 'Preparing the Section 1 production accounts. Users choose passwords after email OTP activation.'
  if [[ "$INTERACTIVE_ACCOUNT_MANIFEST" == true ]]; then printf '%s\n' 'Interactive account mode is enabled; press Enter to keep each documented default.'; else printf '%s\n' 'Using the documented defaults; use --interactive-account-manifest only to customize them.'; fi
  local manifest='[' first=true business_role technical_role username email display_name
  append_account() {
    business_role="$1"; technical_role="$2"
    if [[ "$INTERACTIVE_ACCOUNT_MANIFEST" == true ]]; then username="$(prompt_account_field "${business_role} username" "$3")"; email="$(prompt_account_field "${business_role} email" "$4")"; display_name="$(prompt_account_field "${business_role} display name" "$5")"; else username="$3"; email="$4"; display_name="$5"; fi
    if [[ "$first" == true ]]; then first=false; else manifest+=','; fi
    manifest+="{\"business_role\":\"$(json_escape "$business_role")\",\"username\":\"$(json_escape "$username")\",\"email\":\"$(json_escape "$email")\",\"display_name\":\"$(json_escape "$display_name")\",\"role\":\"$technical_role\"}"
  }
  append_account 'Admin (Team)' ADMIN admin-team team@bridge-ph.com 'Bridge PH Team'
  append_account 'Admin (Alyssa)' ADMIN alyssa.d alyssa.d@bridge-ph.com 'Alyssa D.'
  append_account 'GM' GM carmel.urot carmel.urot@gmail.com 'Carmel C. Urot'
  append_account 'DCS / CEO / Chairman' DCS dan.c.subido dan.c.subido@gmail.com 'Atty. Daniel C. Subido'
  append_account 'Sales (Maker) - Leane' REQUESTER leane.tejero leane.tejero@pimascor.com 'Leane Tejero'
  append_account 'Sales (Maker) - Romeo' REQUESTER romeo.reano romeo.reano@pimascor.com 'Romeo Reano'
  append_account 'Processor (Marcelo Sabando)' REQUESTER processor1 processor1@pimascor.com 'Marcelo Sabando'
  append_account 'Processor (Christian Arcangel)' REQUESTER processor2 processor2@pimascor.com 'Christian Arcangel'
  append_account 'Processor (Jaycee Dimandal)' REQUESTER processor3 processor3@pimascor.com 'Jaycee Dimandal'
  append_account 'Bookkeeper (Michelle Umpacuman)' MICH operations operations@pimascor.com 'Michelle Umpacuman'
  manifest+=']'
  if [[ "$REPLACE_ACCOUNT_MANIFEST" == true ]]; then printf '%s' "$manifest" | podman secret create --replace "$name" - >/dev/null; else printf '%s' "$manifest" | podman secret create "$name" - >/dev/null; fi
  unset manifest username email display_name business_role technical_role
  printf 'Created secret: %s\n' "$name"
}

printf '%s\n' 'Creating missing production secrets as rootless Podman secrets.'
printf '%s\n' 'Values are read interactively and are never written to this repository.'
printf '%s\n' 'The database URL and pgpass secrets are derived automatically from the PostgreSQL secret.'
create_secret bridge_ph_pimascor_postgres_password 'PostgreSQL password'
postgres_password="$(read_secret_value bridge_ph_pimascor_postgres_password)"
[[ -n "$postgres_password" ]] || { printf '%s\n' 'Unable to read the PostgreSQL secret with Podman; recreate it or use a current Podman release.' >&2; exit 1; }
encoded_postgres_password="$(url_encode "$postgres_password")"
escaped_postgres_password="$(pgpass_escape "$postgres_password")"
create_derived_secret bridge_ph_pimascor_database_url "postgresql+psycopg://pimascor:${encoded_postgres_password}@database:5432/pimascor"
create_secret bridge_ph_pimascor_resend_api_key 'Resend API key'
create_secret bridge_ph_pimascor_b2_key_id 'Backblaze B2 key ID'
create_secret bridge_ph_pimascor_b2_application_key 'Backblaze B2 application key'
create_derived_secret bridge_ph_pimascor_pgpass "database:5432:pimascor:pimascor:${escaped_postgres_password}"
unset postgres_password encoded_postgres_password escaped_postgres_password
create_secret bridge_ph_pimascor_restic_password 'Restic backup encryption password (store it safely; losing it prevents backup restore)'
create_account_manifest
printf '%s\n' 'Production secret provisioning complete. Run update-production.sh next.'
