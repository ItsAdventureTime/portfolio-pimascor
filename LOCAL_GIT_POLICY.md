# Local Git policy

The local Git repository is the project's source of truth. The private GitHub
repository is a synchronized off-device mirror, not the authority for
uncommitted or unpublished work.

The local Git repository is the source of truth. The owner has authorized the
private GitHub mirror as a synchronized recovery copy, including approved
NDA/client project materials. Credentials, access tokens, private keys, local
databases, runtime state, and unapproved secrets remain excluded.

- The project owner has authorized this exact private mirror: `https://github.com/ItsAdventureTime/bridge-pimascor.git`.
- GitHub publication uses HTTPS with the GitHub CLI credential helper. Run `gh auth setup-git --hostname github.com`; do not configure an SSH GitHub remote.
- Create commits with local `git commit -S`; use `gh auth setup-git` plus the guarded HTTPS push and `gh api` verification for remote synchronization. GitHub CLI does not provide a separate `gh commit` command.
- The configured pre-push hook blocks every other remote and requires the explicit `PIMASCOR_ALLOW_PRIVATE_GITHUB_PUSH=1` flag for this mirror.
- Never change the remote to a public repository or push NDA material to any other service.
- Use a private, access-controlled, encrypted backup for the working directory and Git metadata. A Git bundle can provide a portable offline copy of committed history, but it does not include uncommitted worktree changes, local configuration, hooks, or the index.
- Review staged files and the staged diff before every commit. Never commit credentials, access tokens, private keys, local databases, runtime output, or active secrets. Client records, supplied reference PDFs, screenshots/photos, and generated handoff packets may be committed only to this exact private mirror.
- If a secret is committed, treat it as exposed: rotate or revoke it first, then use an approved remediation process. Deleting the current file does not remove it from Git history.

## Working conventions

Use local `git` for `add`, `commit`, and history inspection. Use GitHub CLI for
remote authentication, publication, and verification over the HTTPS origin:
`gh auth setup-git --hostname github.com`, `gh auth status`, and
`PIMASCOR_ALLOW_PRIVATE_GITHUB_PUSH=1 git push origin main`. Never replace the
HTTPS GitHub remote with an SSH URL. SSH remains limited to VPS deployment.

1. Keep `main` stable and create a short-lived branch for a focused change.
2. Use small, imperative commit messages, for example `fix(api): reject invalid payment allocation`.
3. Validate the relevant API, web, documentation, or infrastructure change before committing.
4. Create a local annotated release tag only after the related demo or production evidence is accepted.
