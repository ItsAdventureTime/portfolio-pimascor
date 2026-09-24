# Post-change synchronization checklist

This is the default closeout workflow for every project update, revision, or
modification. It applies to source code, tests, infrastructure, deployment
files, documentation, guides, generated handoff artifacts, and repository
configuration.

The goal is to keep the working tree, active documentation, signed local Git
history, and the owner-selected public portfolio GitHub mirror synchronized.

## 1. Search current guidance before acting

Before changing the project, search the web for the latest official guidance,
standards, or frameworks that apply to the change. Prefer primary sources such
as official vendor documentation, standards bodies, and government guidance.
Do not treat a search result as a substitute for the project's local source of
truth.

For this repository's Git workflow, the standing references are:

- [GitHub CLI: `gh auth setup-git`](https://cli.github.com/manual/gh_auth_setup-git)
- [GitHub: About remote repositories](https://docs.github.com/en/get-started/git-basics/about-remote-repositories)
- [GitHub: Signing commits](https://docs.github.com/en/authentication/managing-commit-signature-verification/signing-commits)
- [GitHub: About commit signature verification](https://docs.github.com/en/authentication/managing-commit-signature-verification/about-commit-signature-verification)

If the research changes a security, deployment, accessibility, privacy, or
data-handling decision, update the relevant authoritative document as part of
the same change.

## 2. Inspect the active project state

Before editing:

1. Read the applicable project instructions and the relevant documentation
   index.
2. Confirm `git branch --show-current` is `main`; this repository uses the
   `main` branch locally and remotely. Do not create or switch to a feature,
   release, or work branch. Publish only to `origin/main`.
3. Inspect the current worktree, remote URL, and existing user changes. Confirm
   remote `main` has not moved unexpectedly before publication.
4. Preserve unrelated modifications. Do not stage or overwrite them.
5. Do not read, search, analyze, quote, or use `not-needed/` material.
6. Do not edit or stage
   `production-app/docs/CHATGPT-PIMASCOR-PRODUCTION-HANDOFF-CONTEXT-PROMPT.md`.

## 3. Synchronize documentation and implementation

After the change:

- Update the authoritative Markdown document, guide, index, or runbook that
  describes the changed behavior.
- Add a new guide only when an existing authoritative document cannot clearly
  own the information.
- Remove or revise stale instructions, filenames, commands, and delivery
  references that would mislead the next operator.
- Keep generated artifacts aligned with their source documents and record
  hashes or revision identifiers in manifests where the project uses them.
- Keep client-facing handoffs free of credentials, private keys, secrets,
  infrastructure IP addresses, operator identities, and live production data.

## 4. Validate in the correct execution plane

Run the narrowest useful checks first, then broader checks when the change
warrants them. Use the repository's Docker Sandbox for dependency installs,
package managers, runtimes, builds, tests, lint, migrations, code generation,
and container builds:

```text
jk-sbx-project exec ...
```

The controller creates or reuses the repository sandbox automatically. Do not
use local Podman for development execution. Podman remains valid for remote
VPS production operations and Podman Quadlets. Host-side Git, `gh`, source
editing, and exact sandbox lifecycle commands remain allowed control-plane
operations.

For the selected OrbStack demo, build the combined API/PWA image in the Docker
Sandbox, export it, load it into OrbStack, and verify the public Tunnel route.
For separate VPS production changes, the local release builder must produce
the API image archive and static PWA before transfer. The VPS updater is
activation-only: it loads the supplied image, stages the supplied web
directory, runs the required runtime migrations and health checks, and never
calls podman build.

For documentation-only changes, at minimum run `git diff --check`, review the
staged diff, verify referenced files exist, and run any applicable artifact
inspection or rendering check.

## 5. Create a signed local commit

Before staging, review the exact intended paths and the sensitive-data boundary.
Then run the relevant checks and create a focused signed commit:

```bash
git status --short --branch
git diff --check
git add <reviewed-files>
git diff --cached --check
git diff --cached
git commit -S -m "type(scope): concise change"
```

Commit signatures establish authorship and provenance. GitHub supports GPG,
SSH, and S/MIME commit signatures. Signature method and HTTPS Git transport are
separate concerns: use the approved local signing configuration for the signed
commit, but never use an SSH Git remote or SSH Git transport for this project.

## 6. Publish through authenticated HTTPS GitHub CLI workflow

The owner-selected demo remote is the public HTTPS portfolio repository:

```text
https://github.com/ItsAdventureTime/portfolio-pimascor.git
```

GitHub CLI has no local commit command. Local Git creates the signed commit;
`gh` configures the authenticated HTTPS credential helper, publishes the
commit through the guarded push, and verifies the remote. Run:

```bash
git remote set-url origin https://github.com/ItsAdventureTime/portfolio-pimascor.git
gh auth setup-git --hostname github.com
gh auth status --hostname github.com
PIMASCOR_ALLOW_PORTFOLIO_GITHUB_PUSH=1 git push origin main
```

Before using the guard flag, review the exact commit for public exposure under
`REPOSITORY-EXPOSURE-AND-NDA.md`. Never put tokens, passwords, private keys, or
credentials in a remote URL or repository file. Never use `gh auth token` or
`gh auth status --show-token` in logs or shared output. Never force-push this
repository without explicit authorization.

## 7. Verify local and remote synchronization

After publishing, verify the repository, branch, privacy, authentication, and
commit SHA through GitHub CLI:

```bash
gh auth status --hostname github.com
gh repo view ItsAdventureTime/portfolio-pimascor --json nameWithOwner,isPrivate,defaultBranchRef
git rev-parse HEAD
gh api repos/ItsAdventureTime/portfolio-pimascor/commits/main --jq .sha
git status --short --branch
```

The `git rev-parse HEAD` value must equal the `gh api` SHA. Also verify the
published commit's signature status on GitHub or through the repository's
signature inspection workflow. A remote SHA mismatch means synchronization is
incomplete.

## 8. Finish with a concise handoff

Report what changed, which checks actually ran, the local commit, the remote
verification result, and any remaining unrelated worktree changes. Do not
claim deployment, remote synchronization, or signature verification without
evidence.
