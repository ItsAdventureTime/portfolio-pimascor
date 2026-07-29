#!/bin/sh
set -eu

# Local Mac -> demo VPS source transfer only. The gatewaysentry SSH alias owns
# its username/host settings. Activation is deliberately a separate command
# entered after logging in to the VPS.

SOURCE_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"

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
  app_root=\"/var/home/jk/pimascor-demo\"
  source_dir=\"\$app_root/source\"
  install -d -m 700 \"\$app_root\"
  stage_dir=\"\$(mktemp -d \"\$app_root/.source.next.XXXXXX\")\"
  tar -xzf - -C \"\$stage_dir\"
  find \"\$stage_dir\" -type f \( -name '._*' -o -name '*.pyc' \) -delete
  if [ -e \"\$source_dir\" ] && [ ! -d \"\$source_dir\" ]; then
    printf '%s\\n' \"Refusing to replace unexpected non-directory source path: \$source_dir\" >&2
    exit 1
  fi
  rm -rf -- \"\$source_dir\"
  mv \"\$stage_dir\" \"\$source_dir\"
"

printf '%s\n' 'Source transfer complete. Log in to the VPS, then run:'
printf '%s\n' 'cd /var/home/jk/pimascor-demo/source && ./infra/scripts/update-demo.sh --source /var/home/jk/pimascor-demo/source'
