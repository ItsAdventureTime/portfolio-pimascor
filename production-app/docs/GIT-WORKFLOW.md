# Local and private Git workflow

This repository contains NDA-sensitive project material. The authoritative
remote is the private GitHub repository:

```text
git@github.com:ItsAdventureTime/bridge-pimascor.git
```

## Required sequence for every tracked change

1. Review the worktree and confirm the intended files are the only changes.
2. Run the relevant local checks from `CONTRIBUTING.md`.
3. Commit the change locally with a focused Conventional Commit message.
4. Confirm `origin` still resolves to the private repository above.
5. Push the commit to `main` without force-push.
6. For demo changes, use the committed tree with `infra/scripts/deploy-demo-vps.sh` and then run the documented VPS activation command.

Local Git history is not evidence that the VPS or GitHub received a release.
Remote push output is evidence of GitHub synchronization; VPS command output is
required separately for deployment evidence.

## Exact synchronization commands

Run from the repository root after checks and after committing:

```bash
git remote get-url origin
git status --short
git push origin main
```

The first command must print the private URL shown above. Stop if it prints a
different host or repository. Do not place credentials, tokens, or private keys
in the repository or in deployment scripts.
