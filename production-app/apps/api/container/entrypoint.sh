#!/bin/sh
set -eu

# The Quadlet starts this container only after PostgreSQL has reported healthy.
# Fail fast if a migration is invalid; systemd will retain the failure in the
# journal instead of hiding it behind a one-minute retry loop.
alembic upgrade head

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

exec uvicorn pimascor_api.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'
