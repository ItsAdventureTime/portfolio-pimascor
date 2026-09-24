# Repository exposure and NDA boundary

On 2026-09-24 the owner selected the public
`ItsAdventureTime/portfolio-pimascor` repository as the demo's GitHub target.
Both that repository and the older `ItsAdventureTime/bridge-pimascor` endpoint
reported public visibility and the same `main` SHA during planning. Therefore
no remote in this workflow is a private recovery copy. Verify visibility and
SHA again before each publication; a repo name does not establish privacy.

## Public-safe additions

Application source, tests, generic synthetic demo fixtures, and sanitized
deployment guidance may be published after exact-path review. Do not add
credentials, tokens, private keys, local databases, logs, runtime output,
operator identity details, live production data, or new NDA/client records,
photos, supplied PDFs, or generated client packets to the public mirror.
Keep those outside public assets and new commits. Review every staged binary.

The existing Git history already includes supplied documents and images. This
policy does not assert they are cleared for publication, nor does it erase
them. Removing a file in a new commit leaves previous commits, clones, and
caches intact. If an exposed item requires removal, first classify it with
the owner and follow a separate sensitive-data remediation plan. Rotate or
revoke any exposed credential before considering history changes. Do not
rewrite history or force push without explicit authorization.

Before a signed commit and push, run `git status --short`, inspect
`git diff --cached --name-only` and `git diff --cached`, and run
`git diff --cached --check`. The guarded push and SHA checks are in
`POST-CHANGE-SYNC-CHECKLIST.md`.
