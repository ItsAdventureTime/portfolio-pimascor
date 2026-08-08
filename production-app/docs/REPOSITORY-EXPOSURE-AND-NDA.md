# Repository exposure and NDA boundary

Effective 2026-08-08, this policy separates the local working archive from
the reviewed content published to the private GitHub mirror
(`ItsAdventureTime/bridge-pimascor`). Private visibility is an access control,
not permission to commit client records or credentials.

## Repository-safe content

The remote repository may contain application source, tests, infrastructure
definitions, synthetic demo data, deployment runbooks, design-system guidance,
API contracts, and redacted implementation documentation. These files must not
contain secrets, production data, personal document contents, or unapproved
client attachments.

## Local-only content

The following remain on the encrypted local workspace and are ignored or
untracked from Git:

- meeting/context files containing participant names or NDA requirements;
- financial and operational records such as SOA, budget-request, and payment-verification files;
- screenshots, photos, and `possible-fixes/` evidence;
- supplied quotation-reference PDFs under `docs/reference/`;
- generated production/client handoff packets under `handoff/bridge-pimascor/`;
- credentials, tokens, local databases, logs, and runtime output.

The reference and handoff README files may remain tracked when they contain
only redacted process guidance. Their attached PDFs and client-specific account
details must remain local.

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
Keep generated handoff PDFs and supplied quotation references locally for
controlled review, but never copy them into the public web directory or a
release archive.
