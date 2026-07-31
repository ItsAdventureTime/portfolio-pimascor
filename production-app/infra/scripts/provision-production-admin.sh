#!/usr/bin/env bash
set -Eeuo pipefail

# Run interactively on the production VPS after update-production.sh. The
# account command prompts for the password and does not create fake clients.
APP_CONTAINER="bridge-ph-pimascor-api"
podman exec -it "${APP_CONTAINER}" python -m pimascor_api.seed \
  --username "${1:-admin}" \
  --email "${2:-admin@delegateops.business}" \
  --display-name "${3:-PIMASCOR Administrator}" \
  --role ADMIN
