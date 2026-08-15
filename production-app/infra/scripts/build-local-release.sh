#!/usr/bin/env bash
set -Eeuo pipefail

# Build deployable artifacts in the repository Docker Sandbox. The VPS receives
# the resulting API image archive and static web directory; it does not compile
# or build either application.

SOURCE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPO_ROOT="$(cd "${SOURCE_ROOT}/.." && pwd)"
TIER=""
RELEASE_COMMIT=""
OUTPUT_DIR=""
AMD64_PROBE_IMAGE="docker.io/library/alpine@sha256:14358309a308569c32bdc37e2e0e9694be33a9d99e68afb0f5ff33cc1f695dce"

usage() {
  printf '%s\n' \
    'Usage: build-local-release.sh --tier production|demo --commit SHA --output-dir PATH' \
    '' \
    'Builds the API image and static PWA inside jk-sbx-project, then writes a' \
    'transferable release bundle to PATH.'
}

while (($#)); do
  case "$1" in
    --tier)
      [[ $# -ge 2 ]] || { usage >&2; exit 2; }
      TIER="$2"
      shift 2
      ;;
    --commit)
      [[ $# -ge 2 ]] || { usage >&2; exit 2; }
      RELEASE_COMMIT="$2"
      shift 2
      ;;
    --output-dir)
      [[ $# -ge 2 ]] || { usage >&2; exit 2; }
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown option: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

[[ -n "${TIER}" && -n "${RELEASE_COMMIT}" && -n "${OUTPUT_DIR}" ]] || {
  usage >&2
  exit 2
}
[[ "${RELEASE_COMMIT}" =~ ^[0-9a-f]{40}$ ]] || {
  printf '%s\n' 'Refusing to build: release commit must be a 40-character Git SHA.' >&2
  exit 1
}
[[ -d "${SOURCE_ROOT}/apps/api" && -d "${SOURCE_ROOT}/apps/web" ]] || {
  printf '%s\n' 'Refusing to build: application directories are missing.' >&2
  exit 1
}

case "${TIER}" in
  production)
    api_image="localhost/bridge-ph-pimascor-api:release-${RELEASE_COMMIT}"
    web_args=(
      --build-arg VITE_BASE_PATH=/pimascor/
      --build-arg VITE_API_URL=/pimascor/api/v1
      --build-arg VITE_CSRF_COOKIE_NAME=bridge_ph_pimascor_csrf
      --build-arg VITE_DEPLOYMENT_TIER=production
    )
    ;;
  demo)
    api_image="localhost/bridge-ph-pimascor-demo-api:release-${RELEASE_COMMIT}"
    web_args=(
      --build-arg VITE_BASE_PATH=/pimascor/demo/
      --build-arg VITE_API_URL=/pimascor/demo/api/v1
      --build-arg VITE_CSRF_COOKIE_NAME=bridge_ph_pimascor_demo_csrf
      --build-arg VITE_DEPLOYMENT_TIER=demo
    )
    ;;
  *)
    printf 'Unknown release tier: %s\n' "${TIER}" >&2
    exit 2
    ;;
esac

mkdir -p "${OUTPUT_DIR}"
OUTPUT_DIR="$(cd "${OUTPUT_DIR}" && pwd)"
case "${OUTPUT_DIR}" in
  "${REPO_ROOT}"/*) ;;
  *)
    printf '%s\n' 'Refusing to write release artifacts outside the project workspace.' >&2
    exit 1
    ;;
esac

shopt -s nullglob dotglob
existing_entries=("${OUTPUT_DIR}"/*)
if ((${#existing_entries[@]})); then
  printf 'Refusing to overwrite a non-empty release directory: %s\n' "${OUTPUT_DIR}" >&2
  exit 1
fi
mkdir -p "${OUTPUT_DIR}/web-dist"

output_rel="${OUTPUT_DIR#${REPO_ROOT}/}"
cd "${REPO_ROOT}"
command -v jk-sbx-project >/dev/null 2>&1 || {
  printf '%s\n' 'Refusing to build: jk-sbx-project is not available.' >&2
  exit 1
}

ensure_amd64_execution() {
  local sandbox_arch=""
  if sandbox_arch="$(jk-sbx-project exec docker run --platform linux/amd64 --rm "${AMD64_PROBE_IMAGE}" uname -m 2>/dev/null)" &&
     [[ "${sandbox_arch}" == 'x86_64' ]]; then
    return
  fi

  printf '%s\n' 'Docker Sandbox lacks linux/amd64 execution support; configuring QEMU locally.' >&2
  local apt_ready=false
  for attempt in 1 2 3; do
    if jk-sbx-project exec sudo apt-get update; then
      apt_ready=true
      break
    fi
    [[ "${attempt}" -lt 3 ]] && sleep 2
  done
  [[ "${apt_ready}" == true ]] || {
    printf '%s\n' 'Unable to refresh Docker Sandbox package metadata for QEMU.' >&2
    exit 1
  }
  jk-sbx-project exec sudo apt-get install -y qemu-user-binfmt binfmt-support
  jk-sbx-project exec sudo mount -t binfmt_misc binfmt_misc /proc/sys/fs/binfmt_misc 2>/dev/null || true
  jk-sbx-project exec sudo sh -c 'cat /usr/lib/binfmt.d/qemu-x86_64.conf > /proc/sys/fs/binfmt_misc/register'

  sandbox_arch="$(jk-sbx-project exec docker run --platform linux/amd64 --rm "${AMD64_PROBE_IMAGE}" uname -m 2>/dev/null || true)"
  [[ "${sandbox_arch}" == 'x86_64' ]] || {
    printf '%s\n' 'Docker Sandbox still cannot execute linux/amd64 build steps.' >&2
    printf '%s\n' 'Configure QEMU/binfmt or provide a native amd64 builder, then retry.' >&2
    exit 1
  }
}

ensure_amd64_execution

printf 'Building %s API image in the Docker Sandbox...\n' "${TIER}"
jk-sbx-project exec docker build \
  --platform linux/amd64 \
  --pull \
  --tag "${api_image}" \
  --file production-app/apps/api/Containerfile \
  production-app/apps/api

printf 'Exporting the %s API image archive...\n' "${TIER}"
jk-sbx-project exec docker save \
  --output "${output_rel}/api-image.tar" \
  "${api_image}"

printf 'Building and exporting the %s static PWA in the Docker Sandbox...\n' "${TIER}"
jk-sbx-project exec docker build \
  --platform linux/amd64 \
  --pull \
  --output "type=local,dest=${output_rel}/web-dist" \
  --file production-app/apps/web/Containerfile \
  "${web_args[@]}" \
  production-app/apps/web

[[ -s "${OUTPUT_DIR}/api-image.tar" ]] || {
  printf '%s\n' 'The local API image archive was not created.' >&2
  exit 1
}
for web_file in index.html manifest.webmanifest sw.js; do
  [[ -f "${OUTPUT_DIR}/web-dist/${web_file}" ]] || {
    printf 'The local web build is missing %s.\n' "${web_file}" >&2
    exit 1
  }
done

{
  printf 'tier=%s\n' "${TIER}"
  printf 'commit=%s\n' "${RELEASE_COMMIT}"
  printf 'api_image=%s\n' "${api_image}"
} > "${OUTPUT_DIR}/release-manifest"

printf 'Local release bundle ready: %s\n' "${OUTPUT_DIR}"
