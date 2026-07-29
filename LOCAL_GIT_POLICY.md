# Local Git policy

This repository is intentionally local-only because it contains NDA-covered project materials.

- The project owner has authorized this exact private mirror: `git@github.com:ItsAdventureTime/bridge-pimascor.git`.
- The configured pre-push hook blocks every other remote and requires the explicit `PIMASCOR_ALLOW_PRIVATE_GITHUB_PUSH=1` flag for this mirror.
- Never change the remote to a public repository or push NDA material to any other service.
- Use a private, access-controlled, encrypted backup for the working directory and Git metadata. A Git bundle can provide a portable offline copy of committed history, but it does not include uncommitted worktree changes, local configuration, hooks, or the index.
- Review staged files and the staged diff before every commit. Never commit credentials, access tokens, local databases, or data that has not been approved for retention in this local-only repository.
- If a secret is committed, treat it as exposed: rotate or revoke it first, then use an approved remediation process. Deleting the current file does not remove it from Git history.

## Working conventions

1. Keep `main` stable and create a short-lived branch for a focused change.
2. Use small, imperative commit messages, for example `fix(api): reject invalid payment allocation`.
3. Validate the relevant API, web, documentation, or infrastructure change before committing.
4. Create a local annotated release tag only after the related demo or production evidence is accepted.
