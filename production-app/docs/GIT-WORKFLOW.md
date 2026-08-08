# Local and private Git workflow

This repository contains NDA-sensitive project material. The authoritative
remote is the private GitHub repository:

```text
git@github.com:ItsAdventureTime/bridge-pimascor.git
```

## Required sequence for every tracked change

Before staging, check `docs/REPOSITORY-EXPOSURE-AND-NDA.md`. Client records,
supplied quotation PDFs, screenshots, photos, generated handoff packets,
credentials, local databases, and runtime output are local-only even though
the remote repository is private.

1. Review the worktree and confirm the intended files are the only changes.
2. Run the relevant local checks from `CONTRIBUTING.md`.
3. Commit the change locally with a focused Conventional Commit message.
4. Confirm `origin` still resolves to the private repository above.
5. Run `gh auth setup-git --hostname github.com` so GitHub CLI supplies the
   credential helper used by Git operations.
6. Push the commit to `main` without force-push.
7. Verify GitHub authentication and the published commit with GitHub CLI.
8. For demo changes, use the committed tree with
   `infra/scripts/deploy-demo-vps.sh` and then run the documented VPS
   activation command.

Local Git history is not evidence that the VPS or GitHub received a release.
Remote push output plus a GitHub CLI API verification are evidence of GitHub
synchronization; VPS command output is required separately for deployment
evidence. GitHub CLI is used for authentication and verification; local Git
remains the commit and push transport for this private repository. `gh repo
sync` is not a replacement for publishing local commits; it synchronizes a
repository from another repository or parent branch.

Removing a file from the current tree does not remove it from prior commits.
If a confirmed secret or NDA file was committed historically, stop and use the
approved sensitive-data-removal procedure. History rewriting requires explicit
authorization because it changes commit IDs and may require a force push.

## Exact synchronization commands

Run from the repository root after checks and after committing:

```bash
git remote get-url origin
git status --short
gh auth setup-git --hostname github.com
git push origin main
gh auth status
gh repo view ItsAdventureTime/bridge-pimascor --json nameWithOwner,isPrivate,defaultBranchRef
gh api repos/ItsAdventureTime/bridge-pimascor/commits/main --jq .sha
```

The first command must print the private URL shown above. Stop if it prints a
different host or repository. Do not place credentials, tokens, or private keys
in the repository or in deployment scripts.

The final `gh api` SHA must equal the local `git rev-parse HEAD` output. Never
paste the token printed by `gh auth status` into a command, document, issue, or
log.
