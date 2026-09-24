# Implementation notes

## Source changes

- Pinned the demo database to the official `postgres:18.6-alpine3.23`
  multi-platform manifest, `sha256:e9fcfbcacfa25f66b0eea618adff3c473778463c95ea09bed245f32d4cb613e9`.
  The official image guidance for PostgreSQL 18 uses `/var/lib/postgresql`
  with `PGDATA=/var/lib/postgresql/18/docker`.
- Marked the old production Compose file superseded for the demo. The runbook
  now requires UID 10001 and UID 70 secret-read probes, preserves restrictive
  host permissions, records the ARM64 image build, and marks document flows
  incomplete until private R2 behavior is tested.
- The API already serves the built PWA, retains production security settings
  under `DEPLOYMENT_TIER=demo`, and runs migration, initializer, and reset as
  explicit commands. Existing tests cover restart persistence and explicit
  reset behavior.

## Checks run

- `jk-sbx-project implement 'docker --version && docker compose version'` —
  passed; Docker 29.8.1 and Compose 5.5.1 in the project Sandbox.
- `jk-sbx-project implement 'docker compose ... config --format json'` with
  temporary empty placeholder files outside the checkout — passed. A Python
  assertion checked the PostgreSQL image pin and volume target, no host ports,
  API attachment to `cloudflared-network`, and no added `cloudflared` service.
- `cd production-app/apps/api && uv sync --locked --extra dev` in the project
  Sandbox — passed.
- `cd production-app/apps/api && uv run --locked pytest -q` — all tests passed
  (100%). Warnings: Starlette's TestClient/httpx deprecation and the existing
  `HTTP_422_UNPROCESSABLE_ENTITY` deprecation.
- `cd production-app/apps/web && npm ci` — passed; npm reported 2 dependency
  audit findings (1 moderate, 1 high). No dependency update was made.
- Demo-mode `npm run build` with `/`, `/api/v1`, demo CSRF cookie, and demo tier
  — passed using Vite 8.1.5.
- Built `pimascor-demo-api:latest` in the project Sandbox with
  `--platform linux/arm64`; image inspect reported `linux/arm64` and image ID
  `sha256:aded91d32faf06aad02ceaa129b0b17c46fb6ec536fc747b0d3bf0fdf1e73079`.
  Container inspection confirmed UID/GID 10001 and a non-empty bundled PWA
  `index.html`. Image archive export/transfer was not run.

## Deviations and blockers

- The expected external runtime folder
  `~/docker/portfolio/pimascor/` and its `secrets/` folder do not exist. No
  secret contents were created, read, or copied. Therefore the actual
  non-root secret probes, PostgreSQL startup/health, manual migration/seed/
  reset, API health, restart persistence check, image transfer/load, Tunnel
  network check, and public URL check were not run.
- R2 activation, private bucket, scoped credentials, and document acceptance
  are unverified. The Compose file does not grant R2 credentials. Document
  upload/protected view/delete/reset acceptance is incomplete; do not describe
  the demo as fully functional.
- No deployment was performed. Keep the existing Tunnel and hosted apps
  untouched until the owner supplies/identifies the runtime configuration and
  restrictive secret files pass both UID probes.
- A direct pytest call before locked dependency sync failed with
  `No module named pytest`; the locked `uv sync` then succeeded and the suite
  passed.

## Handoff status

The first `git commit -S` attempt failed because the default agent had no
identities. The Bitwarden desktop SSH-agent socket `~/.bitwarden-ssh-agent.sock`
responds to `ssh-add -L` and lists the configured public signing key. The `bw`
CLI is not installed. A direct SSH signing probe succeeded; then
`SSH_AUTH_SOCK="$HOME/.bitwarden-ssh-agent.sock" git commit -S ...` created
commit `5675ec0b9d08a38dfb883c71178d968cce500332`.

`git verify-commit HEAD` passed locally. The commit was pushed over HTTPS using
the guarded workflow. GitHub's current `main` SHA matched local at publication:
`5675ec0b9d08a38dfb883c71178d968cce500332`. GitHub's commit API reported
`verified: false`, reason `unknown_key`. Checking `user/ssh_signing_keys`
returned HTTP 404 because the current token lacks `admin:ssh_signing_key`; no
additional token scope was requested. The owner may register the signing key
in GitHub to establish GitHub's verification status. GitHub transport remains
HTTPS. No deployment or successful public URL response exists. The reviewer
reported DNS resolution failure. Tunnel and R2 acceptance evidence do not
exist. Independent review is the next role.

## Post-review correction — 2026-09-24

Independent review identified that overriding the PostgreSQL image entrypoint
made its secret probe run as root (UID 0) instead of the postgres user (UID
70). The Compose runbook now passes `--user 70:70`. Confirmed the pinned image
reports UID 0 without the override and UID 70 with it. A temporary Compose
file-backed placeholder-secret probe passed with the corrected command. This
does not prove the absent OrbStack files' actual ownership/read permissions.

The hosting decision no longer says source edits are uncommitted. Reviewer
also observed that the public hostname fails DNS resolution, and that GitHub
reports `unknown_key` although local `git verify-commit` succeeds. The runtime
folder/secrets, Tunnel, public URL, and R2 acceptance remain unresolved; no
deployment claim is supported.

## Final sync — 2026-09-24

- Signed fix commit `4f649cde570b77030299460474fc1bd96776c055` was pushed via
  the guarded HTTPS workflow. `git verify-commit HEAD` passed, local `main`
  matched GitHub `main` at that SHA, and the worktree was clean before this
  handoff update.
- GitHub's commit API still reports `verified: false`, reason `unknown_key`.
  The current `gh` token lacks `admin:ssh_signing_key`; no extra scope was
  requested. The owner must register the Bitwarden-held public key with GitHub
  as a signing key (or resolve GitHub's verification by another approved
  route) to clear that gate. HTTPS remains the Git transport.
- The reviewer follow-up independently validated the corrected UID-70
  placeholder-secret probe and the updated hosting decision. Source verdict:
  conditional pass. Public demo acceptance: fail because DNS/runtime/Tunnel
  and private R2 acceptance are unavailable.

### Smallest owner actions to complete runtime acceptance

1. Create `~/docker/portfolio/pimascor/secrets/` outside the checkout with
   owner-only access and matching PostgreSQL password and URL files. Run both
   UID readability probes; stop if they fail without a restrictive ownership
   solution.
2. Identify the existing OrbStack `cloudflared` container/network, repair the
   hostname DNS/Tunnel route, and confirm its management mode. Do not create
   another Tunnel service.
3. If document flows are required, activate R2 and provide a private bucket
   with a bucket-scoped Object Read & Write S3 token; then configure and test
   multipart upload, protected range reads, delete, and reset cleanup.

## Workspace runtime preparation — 2026-09-25

The reviewer created an ignored runtime folder at
`production-app/infra/docker-compose/.runtime/pimascor-demo/`. A fresh
PostgreSQL password and matching database URL were generated there. A local
check confirmed a 64-character hexadecimal password, matching URL fields,
directory mode `0700`, and secret-file mode `0600`, without logging values.
The Compose copy matches the tracked source. Four unmounted R2 placeholders
identify manual Cloudflare inputs. Existing legacy secret files were not
changed. Do not use the new credentials against an existing DB volume until
its current password and data are accounted for.

Git ignore checks pass for the runtime Compose copy and generated secrets.
The public health request again failed with curl exit 6 because the hostname
does not resolve. OrbStack Docker commands were rejected by the host execution
boundary; no live volume, network, UID mount, startup, or deployment evidence
was obtained. The updated Compose runbook gives the operator the exact next
checks. The repository's public mirror must contain only the ignore rules,
guide, and this redacted status, never the runtime folder.

## OrbStack image preparation and startup gate — 2026-09-25

- Updated the canonical and ignored runtime Compose files to the floating
  `postgres:18-alpine` tag, per owner preference. Official Docker Hub currently
  lists PostgreSQL 18 Alpine tags and its latest 18 Alpine patch. The PostgreSQL
  18 volume remains `/var/lib/postgresql`.
- `jk-sbx-project implement 'docker build --platform linux/arm64 ...'` passed
  for source `c5eb7f24b11949863562ca1cbf54f17f1d86338d`. The built image was
  `linux/arm64`, ID
  `sha256:4f8ee69c75f3ce6e58b57e0aadb8800a596e8fb354bf011db23653f1ce417014`.
  The archive under the ignored runtime images folder passed `gzip -t`.
- `docker --context orbstack image load` passed; OrbStack image inspect matched
  the architecture and ID. OrbStack `docker compose config --quiet` passed.
  Docker engine `orbstack`, `cloudflared`, and `cloudflared-network` were
  present; `pimascor-demo_demo_postgres_data` was absent before startup.
- API UID-10001 and PostgreSQL UID-70 file-secret probes did not run. The host
  guard rejected `docker compose run` and its approved escalation retry with
  “Use jk-sbx-project so Docker execution occurs inside Docker Sandbox.” No
  service was started, and no secrets were printed. Startup is blocked until
  the owner supplies/uses a supported OrbStack host execution path or performs
  the documented probes and initialization manually. API container name for
  the later Tunnel route: `pimascor-demo-api`.

## Independent secret-access check — 2026-09-25

On committed `311766c517f7093357e2f9aa6011587e4c9d43a6`, validation used
disposable file-backed secrets in `jk-sbx-project validate`. Compose config
passed. The `postgres:18-alpine` image pulled successfully. Container root
could read mode `0600` files, mounted as UID/GID `1000:1000`; PostgreSQL UID
70 and API UID 10001 could not. With disposable mode `0640` files and
supplemental GID 1000, both UIDs could read their own mounts. The disposable
validation volume was removed. No actual secret or OrbStack container was
changed. The runbook now includes metadata-only OrbStack probes and keeps
startup blocked until real non-root reads pass.

Local secret pair, directory/file modes, ignored paths, and four R2
placeholders passed recheck without printing credential contents. Public
health still failed DNS resolution (curl exit 6). Local commit signature
passed; GitHub main matched the local SHA but reported `unknown_key`. API/web
tests were not repeated because source code did not change after the earlier
passing run.
