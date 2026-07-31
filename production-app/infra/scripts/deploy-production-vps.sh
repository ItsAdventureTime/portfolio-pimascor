#!/bin/sh
set -eu

SSH_HOST="216.75.75.136"
SSH_USER="jk"
SSH_PORT="22"
SSH_TARGET="${SSH_USER}@${SSH_HOST}"
SOURCE_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"

cd "$SOURCE_ROOT"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
  printf '%s\n' 'Refusing to deploy: production-app is not inside its local Git repository.' >&2
  exit 1
}
if ! git diff --quiet -- . || ! git diff --cached --quiet -- . ||
   [ -n "$(git ls-files --others --exclude-standard -- .)" ]; then
  printf '%s\n' 'Refusing to deploy an uncommitted source tree.' >&2
  exit 1
fi
release_commit="$(git rev-parse HEAD)"
git_root="$(git rev-parse --show-toplevel)"
source_prefix="${SOURCE_ROOT#"${git_root}/"}"
[ "$source_prefix" = 'production-app' ] || {
  printf 'Refusing to deploy unexpected repository path: %s\n' "$source_prefix" >&2
  exit 1
}
cd "$git_root"
git archive --format=tar.gz --add-virtual-file="${source_prefix}/.deployment-source-commit:${release_commit}" HEAD "$source_prefix" |
ssh -o ConnectTimeout=15 -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -p "$SSH_PORT" "$SSH_TARGET" '
  set -eu
  umask 077
  app_root="/var/home/jk/bridge-ph/pimascor"
  source_dir="$app_root/source"
  install -d -m 700 "$app_root"
  stage_dir="$(mktemp -d "$app_root/.source.next.XXXXXX")"
  trap '\''rm -rf -- "$stage_dir"'\'' EXIT
  tar -xzf - --strip-components=1 -C "$stage_dir"
  find "$stage_dir" -type f \( -name "._*" -o -name "*.pyc" \) -delete
  if [ -e "$source_dir" ] && [ ! -d "$source_dir" ]; then
    printf "%s\n" "Refusing to replace unexpected non-directory source path: $source_dir" >&2
    exit 1
  fi
  rm -rf -- "$source_dir"
  mv "$stage_dir" "$source_dir"
  trap - EXIT
'
printf 'Transferred committed production release: %s\n' "$release_commit"
printf '%s\n' 'Log in to the VPS, then run:'
printf '%s\n' 'cd /var/home/jk/bridge-ph/pimascor/source && ./infra/scripts/update-production.sh --source /var/home/jk/bridge-ph/pimascor/source'
