#!/usr/bin/env bash
set -Eeuo pipefail

# Local Docker Sandbox build -> demo VPS transfer. The VPS receives a committed
# source archive plus prebuilt artifacts; it never builds the API or PWA.

SSH_HOST="216.75.75.136"
SSH_USER="jk"
SSH_PORT="22"
SSH_TARGET="${SSH_USER}@${SSH_HOST}"
SOURCE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILD_SCRIPT="${SOURCE_ROOT}/infra/scripts/build-local-release.sh"

cd "${SOURCE_ROOT}"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
  printf '%s\n' 'Refusing to deploy: production-app is not inside its local Git repository.' >&2
  exit 1
}
if ! git diff --quiet -- . || ! git diff --cached --quiet -- . ||
   [ -n "$(git ls-files --others --exclude-standard -- .)" ]; then
  printf '%s\n' 'Refusing to deploy an uncommitted source tree. Review and commit the intended production-app changes first.' >&2
  exit 1
fi

release_commit="$(git rev-parse HEAD)"
git_root="$(git rev-parse --show-toplevel)"
source_prefix="${SOURCE_ROOT#"${git_root}/"}"
[ "${source_prefix}" = 'production-app' ] || {
  printf 'Refusing to deploy unexpected repository path: %s\n' "${source_prefix}" >&2
  exit 1
}
[ -x "${BUILD_SCRIPT}" ] || {
  printf 'Refusing to deploy: local builder is not executable: %s\n' "${BUILD_SCRIPT}" >&2
  exit 1
}

cd "${git_root}"
release_dir="$(mktemp -d "${SOURCE_ROOT}/.deployment-artifacts.demo.XXXXXX")"
cleanup_release_dir() {
  rm -rf -- "${release_dir}"
}
trap cleanup_release_dir EXIT

"${BUILD_SCRIPT}" \
  --tier demo \
  --commit "${release_commit}" \
  --output-dir "${release_dir}"

git archive \
  --format=tar.gz \
  --add-virtual-file="${source_prefix}/.deployment-source-commit:${release_commit}" \
  HEAD "${source_prefix}" > "${release_dir}/source.tar.gz"

tar_options=(-czf -)
if [ "$(uname -s)" = Darwin ]; then
  tar_options+=(--no-xattrs --no-mac-metadata)
fi
tar "${tar_options[@]}" \
  -C "${release_dir}" \
  source.tar.gz \
  api-image.tar \
  release-manifest \
  web-dist \
| ssh \
  -o ConnectTimeout=15 \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  -p "${SSH_PORT}" \
  "${SSH_TARGET}" '
  set -eu
  umask 077
  app_root="/var/home/jk/bridge-ph/pimascor-demo"
  source_dir="$app_root/source"
  artifact_root="$app_root/release-artifacts"
  install -d -m 700 "$app_root" "$artifact_root"
  stage_dir="$(mktemp -d "$app_root/.release.next.XXXXXX")"
  bundle_stage=""
  cleanup() {
    rm -rf -- "$stage_dir"
    if [ -n "$bundle_stage" ]; then
      rm -rf -- "$bundle_stage"
    fi
  }
  trap cleanup EXIT
  tar -xzf - -C "$stage_dir"
  mkdir "$stage_dir/source"
  tar -xzf "$stage_dir/source.tar.gz" --strip-components=1 -C "$stage_dir/source"
  find "$stage_dir/source" -type f \( -name "._*" -o -name "*.pyc" \) -delete
  release_commit="$(tr -d "\r\n" < "$stage_dir/source/.deployment-source-commit")"
  printf "%s" "$release_commit" | grep -Eq "^[0-9a-f]{40}$" || {
    printf "%s\n" "Refusing to install a release with an invalid Git marker." >&2
    exit 1
  }
  grep -Fqx "tier=demo" "$stage_dir/release-manifest" || {
    printf "%s\n" "Refusing to install an artifact for a different deployment tier." >&2
    exit 1
  }
  grep -Fqx "commit=$release_commit" "$stage_dir/release-manifest" || {
    printf "%s\n" "Refusing to install artifacts that do not match the source commit." >&2
    exit 1
  }
  grep -Fqx "api_image=localhost/bridge-ph-pimascor-demo-api:release-$release_commit" "$stage_dir/release-manifest" || {
    printf "%s\n" "Refusing to install an unexpected demo API image." >&2
    exit 1
  }
  [ -s "$stage_dir/api-image.tar" ] || {
    printf "%s\n" "The transferred demo API image archive is empty." >&2
    exit 1
  }
  [ -f "$stage_dir/web-dist/index.html" ] &&
    [ -f "$stage_dir/web-dist/manifest.webmanifest" ] &&
    [ -f "$stage_dir/web-dist/sw.js" ] || {
      printf "%s\n" "The transferred demo web bundle is incomplete." >&2
      exit 1
    }
  bundle_stage="$(mktemp -d "$artifact_root/.bundle.next.XXXXXX")"
  mv "$stage_dir/api-image.tar" "$bundle_stage/api-image.tar"
  mv "$stage_dir/release-manifest" "$bundle_stage/release-manifest"
  mv "$stage_dir/web-dist" "$bundle_stage/web-dist"
  bundle_dir="$artifact_root/$release_commit"
  if [ -e "$bundle_dir" ] && [ ! -d "$bundle_dir" ]; then
    printf "%s\n" "Refusing to replace unexpected artifact path: $bundle_dir" >&2
    exit 1
  fi
  rm -rf -- "$bundle_dir"
  mv "$bundle_stage" "$bundle_dir"
  bundle_stage=""
  if [ -e "$source_dir" ] && [ ! -d "$source_dir" ]; then
    printf "%s\n" "Refusing to replace unexpected non-directory source path: $source_dir" >&2
    exit 1
  fi
  rm -rf -- "$source_dir"
  mv "$stage_dir/source" "$source_dir"
  printf "Installed committed demo source and artifacts: %s\n" "$release_commit"
  printf "Artifact bundle: %s\n" "$bundle_dir"
'

printf 'Transferred committed demo source and local build artifacts: %s\n' "${release_commit}"
artifact_dir="/var/home/jk/bridge-ph/pimascor-demo/release-artifacts/${release_commit}"
printf 'Release commit: %s\n' "${release_commit}"
printf 'Artifact bundle: %s\n' "${artifact_dir}"
printf '%s\n' 'Activation remains a separate VPS step; follow docs/DEMO-VPS-DEPLOYMENT.md.'
