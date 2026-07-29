#!/bin/sh
set -eu

# One-command local Mac -> demo VPS release. The gatewaysentry SSH alias owns
# its username/host settings and prompts for the VPS password exactly once.
# A timestamped source release is retained on the VPS; this script never
# deletes an existing release or the live demo data directory.

SOURCE_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
RELEASE_STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

cd "$SOURCE_ROOT"

tar \
  --exclude='./.git' \
  --exclude='./apps/web/node_modules' \
  --exclude='./apps/web/dist' \
  --exclude='./apps/api/.venv' \
  --exclude='./apps/api/var' \
  --exclude='./apps/api/.pytest_cache' \
  --exclude='*/__pycache__' \
  -czf - . \
| ssh gatewaysentry "
  set -eu
  umask 077
  release_root=\"\$HOME/bridge-ph/releases\"
  release_dir=\"\$release_root/pimascor-demo-${RELEASE_STAMP}\"
  mkdir -p \"\$release_dir\"
  tar -xzf - -C \"\$release_dir\"
  cd \"\$release_dir\"
  ./infra/scripts/update-demo.sh --source \"\$release_dir\"
"
