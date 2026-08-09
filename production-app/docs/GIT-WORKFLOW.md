# Local and private Git workflow

This repository contains NDA-sensitive project material. The local Git
repository and its checked-out, reviewed `main` branch are the source of truth.
The private GitHub repository is the synchronized remote mirror:

```text
https://github.com/ItsAdventureTime/bridge-pimascor.git
```

## Required sequence for every tracked change

Before staging, check `docs/REPOSITORY-EXPOSURE-AND-NDA.md`. Client records,
supplied quotation PDFs, screenshots, photos, and generated handoff packets are
allowed in the authorized private mirror. Credentials, private keys, local
databases, and runtime output remain prohibited.

1. Review the worktree and confirm the intended files are the only changes.
2. Run the relevant local checks from `CONTRIBUTING.md`.
3. Commit the change locally with a focused Conventional Commit message.
4. Confirm `origin` still resolves to the HTTPS private repository above.
5. Run `gh auth setup-git --hostname github.com`; GitHub CLI supplies the
   authenticated HTTPS credential helper used by Git operations.
6. Push the commit to `main` without force-push, using the repository's
   explicit private-push guard.
7. Verify GitHub authentication and the published commit with GitHub CLI.
8. For demo changes, use the committed tree with
   `infra/scripts/deploy-demo-vps.sh` and then run the documented VPS
   activation command.

Local Git history is the authoritative change record, but it is not evidence
that the VPS or GitHub received a release.
Remote push output plus a GitHub CLI API verification are evidence of GitHub
synchronization; VPS command output is required separately for deployment
evidence. GitHub CLI supplies HTTPS credentials and verifies the mirror; local Git
remains the commit and push transport for this private repository. `gh repo
sync` is not a replacement for publishing local commits; it synchronizes a
repository from another repository or parent branch.

### Signature requirement

Commits must be SSH-signed with the signing key registered on the GitHub
account. Confirm the local commit with `git log --show-signature -1`, then
confirm the remote API reports `commit.verification.verified=true`. `gh auth
setup-git` supplies GitHub HTTPS credentials; it does not create or sign commits. If
the configured 1Password SSH signer is locked or unavailable, unlock it before
committing. Do not fall back to an unsigned commit merely to make the push
succeed.

Removing a file from the current tree does not remove it from prior commits.
If a confirmed secret or NDA file was committed historically, stop and use the
approved sensitive-data-removal procedure. History rewriting requires explicit
authorization because it changes commit IDs and may require a force push.

## Exact synchronization commands

Run from the repository root after checks and after committing:

```bash
git remote get-url origin
git status --short
git remote set-url origin https://github.com/ItsAdventureTime/bridge-pimascor.git
gh auth setup-git --hostname github.com
PIMASCOR_ALLOW_PRIVATE_GITHUB_PUSH=1 git push origin main
gh auth status
gh repo view ItsAdventureTime/bridge-pimascor --json nameWithOwner,isPrivate,defaultBranchRef
gh api repos/ItsAdventureTime/bridge-pimascor/commits/main --jq .sha
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
command transfers the committed production tree; the VPS command activates it.
Do not describe local build output as proof of VPS deployment.

**Run on macOS:**

```bash
/Users/jk.deguzman/dev/bridge-ph_Dashboard/production-app/infra/scripts/deploy-production-vps.sh
```

**Run after logging into the VPS:**

```bash
cd /var/home/jk/bridge-ph/pimascor/source && ./infra/scripts/provision-production-secrets.sh && ./infra/scripts/update-production.sh --source /var/home/jk/bridge-ph/pimascor/source && ./infra/scripts/install-production-caddy.sh
```

If the approved account manifest changed, the Mac command must use
`--refresh-account-manifest`; secrets, migrations, and account bootstrap remain
idempotent according to `PRODUCTION-VPS-DEPLOYMENT.md`.
