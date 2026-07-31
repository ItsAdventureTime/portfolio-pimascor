#!/usr/bin/env bash
set -Eeuo pipefail

# Emergency/manual fallback only. Normal production accounts are created by
# the account-bootstrap Quadlet from bridge_ph_pimascor_account_bootstrap and
# activated by the user through email OTP; this helper prompts for a password.
APP_CONTAINER="bridge-ph-pimascor-api"
podman exec -it "${APP_CONTAINER}" python -m pimascor_api.seed \
  --username "${1:-admin}" \
  --email "${2:-admin@delegateops.business}" \
  --display-name "${3:-PIMASCOR Administrator}" \
  --role ADMIN
