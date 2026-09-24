#!/bin/sh
set -eu

# Keep runtime startup separate from maintenance commands. Existing hosted
# runtimes retain automatic migration/reset behavior; the manual Compose demo
# sets AUTO_MIGRATE=false and runs each initialization step explicitly.
if [ "${AUTO_MIGRATE:-true}" = "true" ]; then
  alembic upgrade head

  if [ "${DEPLOYMENT_TIER:-}" = "demo" ]; then
    python -m pimascor_api.demo_initializer
    python -m pimascor_api.demo_reset
  fi
fi

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

exec uvicorn pimascor_api.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'
