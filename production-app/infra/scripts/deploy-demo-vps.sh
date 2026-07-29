#!/bin/sh
set -eu

# Local Mac -> demo VPS source transfer only. The gatewaysentry SSH alias owns
# its username/host settings. Activation is deliberately a separate command
# entered after logging in to the VPS.

SOURCE_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
RELEASE_STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

cd "$SOURCE_ROOT"

# macOS tar otherwise writes Apple metadata (xattrs/ACLs/AppleDouble sidecars)
# into the stream. Linux tar warns about those headers and an AppleDouble file
# ending in .py can make Alembic try to import binary bytes as a migration.
COPYFILE_DISABLE=1 tar \
  --no-mac-metadata \
  --no-xattrs \
  --no-acls \
  --no-fflags \
  --exclude='./.git' \
  --exclude='./.DS_Store' \
  --exclude='./._*' \
  --exclude='*/._*' \
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
  release_root=\"/var/home/jk/bridge-ph\"
  stage_dir=\"\$(mktemp -d \"\$release_root/.pimascor-demo-release.next.XXXXXX\")\"
  tar -xzf - -C \"\$stage_dir\"
  find \"\$stage_dir\" -type f \( -name '._*' -o -name '*.pyc' \) -delete
  if [ -d \"\$release_root/pimascor-demo-release\" ]; then
    mv \"\$release_root/pimascor-demo-release\" \"\$release_root/pimascor-demo-release.previous.${RELEASE_STAMP}\"
  fi
  mv \"\$stage_dir\" \"\$release_root/pimascor-demo-release\"
"

printf '%s\n' 'Source transfer complete. Log in to the VPS, then run:'
printf '%s\n' 'cd /var/home/jk/bridge-ph/pimascor-demo-release && ./infra/scripts/update-demo.sh --source /var/home/jk/bridge-ph/pimascor-demo-release'
