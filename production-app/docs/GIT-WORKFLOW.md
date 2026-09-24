# Local and public portfolio Git workflow

This repository contains material that requires public-exposure review. The
local Git repository and its checked-out, reviewed `main` branch are the source
of truth. The owner-selected public demo mirror is:

```text
https://github.com/ItsAdventureTime/portfolio-pimascor.git
```

## Required sequence for every tracked change

**Default rule:** after every update, revision, or modification, follow
[`POST-CHANGE-SYNC-CHECKLIST.md`](POST-CHANGE-SYNC-CHECKLIST.md). Search current
official guidance before acting, update the relevant documentation and guides,
validate the change, create a signed local commit, publish it through the
authenticated HTTPS workflow, and verify the remote SHA.

**Transport rule:** create signed commits with local `git` commands. Publish the
already-created commit with GitHub CLI over the HTTPS `origin`; do not use an
SSH GitHub remote or SSH Git transport. `gh auth setup-git
--hostname github.com` configures Git to use the authenticated GitHub CLI
credential helper. Authentication must still be verified with `gh auth status`;
do not assume a machine is authenticated.

Before staging, check `docs/REPOSITORY-EXPOSURE-AND-NDA.md`. Do not add new
client records, supplied PDFs, photos, or generated packets to the public
mirror. Credentials, private keys, local databases, and runtime output remain
prohibited.

1. Review the worktree and confirm the intended files are the only changes.
2. Run the relevant local checks from `CONTRIBUTING.md`.
3. Commit the change locally with a focused signed Conventional Commit message.
4. Confirm `origin` resolves to the HTTPS portfolio repository above.
5. Run `gh auth setup-git --hostname github.com`; GitHub CLI supplies the
   authenticated HTTPS credential helper used by Git operations.
6. Push the commit to `main` without force-push, using the repository's
   explicit portfolio-push guard.
7. Verify GitHub authentication and the published commit with GitHub CLI.
8. For demo changes, follow `DEMO-HOSTING-DECISION-2026-09-24.md` and
   `../infra/docker-compose/README.md`. Build the combined API/PWA image in
   the Docker Sandbox, then load and run it in OrbStack. Confirm the public
   Tunnel route separately from Git publication.

The responsibility is intentionally split: local Git creates the commit;
GitHub CLI authenticates and verifies publication to the HTTPS remote.
GitHub CLI has no separate `gh commit` operation, so do not invent one or put
tokens into a URL. `gh auth setup-git` configures Git's credential helper, and
the guarded HTTPS push publishes the already-created local commit.

Local Git history is the authoritative change record, but it is not evidence
that the VPS or GitHub received a release.
Remote push output plus a GitHub CLI API verification are evidence of GitHub
synchronization; VPS command output is required separately for deployment
evidence. GitHub CLI supplies HTTPS credentials and verifies the mirror; local Git
remains the commit and push transport for this public portfolio repository. `gh repo
sync` is not a replacement for publishing local commits; it synchronizes a
repository from another repository or parent branch.

### Commit authentication

Use the configured local signing key for `git commit -S`; signing format and
Git transport are separate. GitHub CLI authenticates the HTTPS remote through
its credential helper. Verify the published commit with `gh api`; do not put
credentials in a URL or repository file.

Removing a file from the current tree does not remove it from prior commits.
If a confirmed secret or NDA file was committed historically, stop and use a
separate owner-reviewed sensitive-data-removal procedure. History rewriting
requires explicit authorization because it changes commit IDs and may require
a force push.

## Exact synchronization commands

Run from the repository root after checks and after committing:

```bash
git add <reviewed-files>
git commit -S -m "type(scope): concise change"
git remote get-url origin
git status --short
git remote set-url origin https://github.com/ItsAdventureTime/portfolio-pimascor.git
gh auth setup-git --hostname github.com
PIMASCOR_ALLOW_PORTFOLIO_GITHUB_PUSH=1 git push origin main
gh auth status
gh repo view ItsAdventureTime/portfolio-pimascor --json nameWithOwner,isPrivate,defaultBranchRef
gh api repos/ItsAdventureTime/portfolio-pimascor/commits/main --jq .sha
```

The remote must print the HTTPS URL shown above. Stop if it prints a different
host, protocol, or repository. Do not place credentials, tokens, or private keys
in the repository or in deployment scripts.

The final `gh api` SHA must equal the local `git rev-parse HEAD` output. Never
paste the token printed by `gh auth status` into a command, document, issue, or
log.

## Required deployment handoff for production changes

Every response that changes production code, infrastructure, or deployment
configuration must include both commands below, clearly labelled. The Mac
command builds and transfers the committed production source plus artifacts; the
VPS command activates those artifacts. Do not describe local build output as
proof of VPS deployment.

**Run on macOS:**

```bash
/Users/jk.deguzman/dev/bridge-ph_Dashboard/production-app/infra/scripts/deploy-production-vps.sh
```

**Run after logging into the VPS:**

```bash
cd /var/home/jk/bridge-ph/pimascor/source && ./infra/scripts/provision-production-secrets.sh
cd /var/home/jk/bridge-ph/pimascor/source && ./infra/scripts/update-production.sh --source /var/home/jk/bridge-ph/pimascor/source --api-image-archive /var/home/jk/bridge-ph/pimascor/release-artifacts/COMMIT/api-image.tar --web-dist /var/home/jk/bridge-ph/pimascor/release-artifacts/COMMIT/web-dist
cd /var/home/jk/bridge-ph/pimascor/source && ./infra/scripts/install-production-caddy.sh
```

If the approved account manifest changed, the Mac command must use
`--refresh-account-manifest`. Replace `COMMIT` with the release SHA, or copy the
exact artifact paths printed by the transfer script. Secrets, migrations, and
account bootstrap remain idempotent according to
`PRODUCTION-VPS-DEPLOYMENT.md`.
