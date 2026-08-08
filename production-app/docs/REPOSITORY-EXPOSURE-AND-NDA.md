# Repository exposure and NDA boundary

Effective 2026-08-08, the local Git repository is the source of truth and the
private GitHub mirror (`ItsAdventureTime/bridge-pimascor`) is its synchronized
cross-computer recovery copy. Private visibility is required for approved
NDA/client material, but it is not permission to commit credentials.

## Repository-safe content

The remote repository may contain application source, tests, infrastructure
definitions, synthetic demo data, deployment runbooks, design-system guidance,
API contracts, approved NDA/client records, supplied references, screenshots,
photos, and generated handoff packets. These materials are for this private
mirror only and must not be published or copied into public web assets.

## Always-excluded content

The following remain excluded from both local commits and the remote:

- credentials, tokens, private keys, local databases, logs, runtime output, and active secrets.

Client-specific files are allowed because this repository is private and
explicitly authorized. Review every staged binary before committing.

## Required checks

```bash
git status --short
git diff --cached --check
git diff --cached --name-only
```

Review every staged path before committing. Enable GitHub Secret Protection and
push protection for the private repository when the plan allows it.

## Historical exposure

`git rm --cached` and a new commit remove a path from the current tree only.
Earlier commits, clones, forks, pull requests, and cached GitHub objects may
still contain it. Do not rewrite history automatically. If a confirmed secret
was committed, revoke or rotate it first, obtain explicit authorization for a
history rewrite, coordinate other clones, and follow GitHub's sensitive-data
removal procedure. A rewrite changes commit IDs and requires a coordinated
force push.

## Demo handoff rule

The demo deploy script transfers source/build artifacts, not the client packet.
Keep generated handoff PDFs and supplied quotation references out of the public
web directory and release archives, even though they are retained in this
private Git mirror.
