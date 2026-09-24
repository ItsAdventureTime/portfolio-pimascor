# Repository backup and recovery

This project uses the local Git repository as its source of truth. The
owner-selected portfolio GitHub repository is public and is a synchronization
target, not a confidential backup. Keep an independent encrypted recovery
copy with appropriate access and retention.

## What belongs in GitHub

Keep reviewed application source, tests, migrations, deployment definitions,
redacted documentation, and reproducible configuration in the public
portfolio repository. Never commit passwords, Podman secret values, VPS keys, live
databases, client records, uploaded documents, reset tokens, or unreviewed NDA
evidence.

The root `.gitignore` and `docs/REPOSITORY-EXPOSURE-AND-NDA.md` define the
current boundary. The public repository exposes its full Git history.

## GitHub continuity check

Run from the repository root:

```bash
gh auth status
gh repo view ItsAdventureTime/portfolio-pimascor --json nameWithOwner,isPrivate,visibility,viewerPermission
git remote get-url origin
git rev-parse HEAD
gh api repos/ItsAdventureTime/portfolio-pimascor/commits/main --jq .sha
```

The repository must report `PUBLIC`, `ADMIN` for the owner, the approved
remote, and a remote SHA equal to the local `HEAD`.

## Independent encrypted mirror

GitHub's documented mirror method preserves the Git repository and history:

```bash
gh auth setup-git --hostname github.com
git clone --mirror https://github.com/ItsAdventureTime/portfolio-pimascor.git /secure/backup/portfolio-pimascor.git
```

Place that mirror on an encrypted disk or approved encrypted backup service.
Do not store it in the project worktree, a public bucket, or an unencrypted
USB drive. If Git LFS is ever introduced, fetch its objects as part of the
mirror backup.

The mirror does not contain ignored local-only NDA files, VPS secrets, local
configuration, or uncommitted work. Back those up separately through an
approved encrypted process, with retention and access records.

## Restore check

Restore into a new temporary directory, never over the active workspace:

```bash
git clone /secure/backup/portfolio-pimascor.git /secure/restore/portfolio-pimascor-check
cd /secure/restore/portfolio-pimascor-check
git fsck --full
git log -1 --oneline
```

Reapply local-only files and secrets only through their approved secure
channels. Never commit them to make a restore appear complete.

## Exposure response

If a secret or live NDA record enters Git history, treat it as exposed: revoke
or rotate the credential first, preserve incident evidence, and then use an
approved history-removal procedure. A normal deletion commit does not erase
older Git objects and a history rewrite changes commit IDs and requires
coordination.

This runbook follows GitHub's repository-backup and access-control guidance,
and the project's NDA boundary. It is operational guidance, not legal advice.
