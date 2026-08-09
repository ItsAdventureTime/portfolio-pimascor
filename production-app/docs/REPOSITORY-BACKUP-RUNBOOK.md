# Private repository backup and recovery

This project uses the local Git repository as its source of truth and the
private GitHub repository as a controlled continuity mirror, not as the only
backup location. Private visibility limits access, but
does not replace encryption, account protection, retention, or an independent
recovery copy.

## What belongs in GitHub

Keep reviewed application source, tests, migrations, deployment definitions,
redacted documentation, and reproducible configuration in the private
repository. Never commit passwords, Podman secret values, VPS keys, live
databases, client records, uploaded documents, reset tokens, or unreviewed NDA
evidence.

The root `.gitignore` and `docs/REPOSITORY-EXPOSURE-AND-NDA.md` define the
current boundary. A private repository is still a complete copy of its Git
history for every person or service with access.

## GitHub continuity check

Run from the repository root:

```bash
gh auth status
gh repo view ItsAdventureTime/bridge-pimascor --json nameWithOwner,isPrivate,visibility,viewerPermission
git remote get-url origin
git rev-parse HEAD
gh api repos/ItsAdventureTime/bridge-pimascor/commits/main --jq .sha
```

The repository must report `PRIVATE`, `ADMIN` for the owner, the approved
remote, and a remote SHA equal to the local `HEAD`.

## Independent encrypted mirror

GitHub's documented mirror method preserves the Git repository and history:

```bash
gh auth setup-git --hostname github.com
git clone --mirror https://github.com/ItsAdventureTime/bridge-pimascor.git /secure/backup/bridge-pimascor.git
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
git clone /secure/backup/bridge-pimascor.git /secure/restore/bridge-pimascor-check
cd /secure/restore/bridge-pimascor-check
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
