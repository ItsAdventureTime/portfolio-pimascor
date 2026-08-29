#!/usr/bin/env bash
set -Eeuo pipefail

# Static contract check for the VPS-only installer. Live Caddy/Podman checks
# run when install-demo-caddy.sh executes on the VPS.
SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/install-demo-caddy.sh"
grep -Fq 'set -Eeuo pipefail' "${SCRIPT}"
grep -Fq 'CADDY_IMAGE="$(awk -F= '\''/^Image=/{print $2; exit}'\'' "${CADDY_QUADLET}")"' "${SCRIPT}"
grep -Fq '[[ "${CADDY_IMAGE}" == *@sha256:* ]]' "${SCRIPT}"
grep -Fq 'PODMAN_SYSTEM_GENERATOR="${PODMAN_SYSTEM_GENERATOR:-/usr/lib/systemd/system-generators/podman-system-generator}"' "${SCRIPT}"
grep -Fq 'QUADLET_UNIT_DIRS="${quadlet_root}" "${PODMAN_SYSTEM_GENERATOR}" --user --dryrun' "${SCRIPT}"
grep -Fq 'mv -f "${temp}" "${target}"' "${SCRIPT}"
grep -Fq 'bridge-ph-pimascor-demo-proxy.network' "${SCRIPT}"
grep -Fq '%h/bridge-ph/pimascor-demo/web-dist:/srv/bridge-ph-pimascor-demo:ro,Z' "${SCRIPT}"
grep -Fq 'restart bridge-ph-pimascor-demo-proxy-network.service' "${SCRIPT}"
grep -Fq 'https://delegateops.business/demo/pimascor' "${SCRIPT}"
grep -Fq 'https://delegateops.business/demo/pimascor/api/v1/health' "${SCRIPT}"

fixture_root="$(mktemp -d)"
trap 'rm -rf -- "${fixture_root}"' EXIT
quadlet_input="${fixture_root}/quadlet.input"
quadlet_output="${fixture_root}/quadlet.output"
cat >"${quadlet_input}" <<'EOF'
[Unit]
Description=fixture

[Service]
Network=bridge-ph-pimascor-demo-proxy.network
Volume=%h/old:/srv/bridge-ph-pimascor-demo:ro,Z
Environment=KEEP_ME=yes

[Container]
Image=registry.example/caddy@sha256:abc
Network=bridge-ph-pimascor-demo-proxy.network
Volume=%h/bridge-ph/pimascor-demo/web-dist:/srv/bridge-ph-pimascor-demo:ro,Z
EOF
PIMASCOR_INSTALL_DEMO_CADDY_NORMALIZE_ONLY=1 "${SCRIPT}" "${quadlet_input}" "${quadlet_output}"
grep -Fxq '[Service]' "${quadlet_output}"
grep -Fxq 'Environment=KEEP_ME=yes' "${quadlet_output}"
[[ "$(grep -Ec '^Network=bridge-ph-pimascor-demo-proxy\.network$' "${quadlet_output}")" -eq 1 ]]
[[ "$(grep -Ec '^Volume=%h/bridge-ph/pimascor-demo/web-dist:/srv/bridge-ph-pimascor-demo:ro,Z$' "${quadlet_output}")" -eq 1 ]]
awk '/^\[Container\]$/{container=1; next} /^\[/{container=0} /^Network=bridge-ph-pimascor-demo-proxy\.network$|^Volume=%h\/bridge-ph\/pimascor-demo\/web-dist:/{if (!container) exit 1} END{exit 0}' "${quadlet_output}"

live_root="${fixture_root}/live"
stub_bin="${fixture_root}/bin"
mkdir -p "${stub_bin}"
cat >"${stub_bin}/uname" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' Linux
EOF
cat >"${stub_bin}/systemctl" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == *'show --property=LoadState --value caddy.service'* ]]; then
  printf '%s\n' loaded
  exit 0
fi
exit 1
EOF
cat >"${stub_bin}/podman" <<EOF
#!/usr/bin/env bash
printf '%s\n' "\$*" >"${fixture_root}/podman.args"
exit 1
EOF
chmod 755 "${stub_bin}/uname" "${stub_bin}/systemctl" "${stub_bin}/podman"
generator="${fixture_root}/generator"
printf '%s\n' '#!/usr/bin/env bash' 'exit 0' >"${generator}"
chmod 755 "${generator}"
mkdir -p "${live_root}/conf" "${live_root}/home/.config/containers/systemd/caddy" "${live_root}/home/bridge-ph/pimascor-demo/web-dist"
printf '%s\n' 'delegateops.business {' '}' >"${live_root}/conf/Caddyfile"
printf '%s\n' 'Image=registry.example/caddy@sha256:abc' '[Container]' >"${live_root}/home/.config/containers/systemd/caddy/caddy.container"
printf '%s\n' 'sentinel' >"${live_root}/conf/bridge-ph-pimascor-demo.Caddyfile"
printf '%s\n' 'reverse_proxy bridge-ph-pimascor-demo-api:8000' 'root * /srv/bridge-ph-pimascor-demo' '}' >"${fixture_root}/invalid-handlers"
# Keep byte-for-byte snapshots; a checksum collision must not make a mutation
# look like a no-op.
before_caddy="${fixture_root}/before-Caddyfile"
before_handlers="${fixture_root}/before-demo-handlers"
before_quadlet="${fixture_root}/before-caddy.container"
cp "${live_root}/conf/Caddyfile" "${before_caddy}"
cp "${live_root}/conf/bridge-ph-pimascor-demo.Caddyfile" "${before_handlers}"
cp "${live_root}/home/.config/containers/systemd/caddy/caddy.container" "${before_quadlet}"
# This stub intentionally makes `podman run ... caddy validate` fail. It tests
# command construction and the installer's pre-install abort path; it does not
# parse a Caddyfile. Real Caddy parsing is covered by the VPS validation command.
if PATH="${stub_bin}:${PATH}" HOME="${live_root}/home" PIMASCOR_CADDY_CONF_ROOT="${live_root}/conf" PIMASCOR_CADDY_QUADLET="${live_root}/home/.config/containers/systemd/caddy/caddy.container" PIMASCOR_DEMO_HANDLERS="${fixture_root}/invalid-handlers" PODMAN_SYSTEM_GENERATOR="${generator}" PIMASCOR_INSTALL_DEMO_CADDY_TEST_MODE=1 "${SCRIPT}" 2>"${fixture_root}/installer.err"; then
  printf '%s\n' 'Expected the stubbed podman validation command to fail.' >&2
  exit 1
fi
[[ -f "${fixture_root}/podman.args" ]] || { printf '%s\n' 'Stubbed podman was not invoked.' >&2; cat "${fixture_root}/installer.err" >&2; exit 1; }
grep -Fq 'caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile' "${fixture_root}/podman.args" || {
  printf '%s\n' 'Installer did not invoke the expected Caddy validation command.' >&2
  cat "${fixture_root}/podman.args" >&2
  exit 1
}
cmp -s "${before_caddy}" "${live_root}/conf/Caddyfile" || { printf '%s\n' 'Installer mutated Caddyfile before validation failure.' >&2; exit 1; }
cmp -s "${before_handlers}" "${live_root}/conf/bridge-ph-pimascor-demo.Caddyfile" || { printf '%s\n' 'Installer mutated demo handlers before validation failure.' >&2; exit 1; }
cmp -s "${before_quadlet}" "${live_root}/home/.config/containers/systemd/caddy/caddy.container" || { printf '%s\n' 'Installer mutated Caddy Quadlet before validation failure.' >&2; exit 1; }
printf '%s\n' 'Demo Caddy installer static contract passed.'
