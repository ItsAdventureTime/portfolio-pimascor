# Local Git policy

The local repository is the working source of truth. The owner selected the
public HTTPS portfolio mirror `https://github.com/ItsAdventureTime/portfolio-pimascor.git`
for this demo on 2026-09-24. Do not assume GitHub visibility is private.

Always work on `main` locally and publish to `origin/main`. Make focused
commits directly on the local `main` branch; do not create or switch to feature
branches for this repository. Before editing, committing, or pushing, verify
the local branch and remote `main` state. If either is not the expected `main`
line, stop and reconcile without rewriting history.

After every tracked change, follow
`production-app/docs/POST-CHANGE-SYNC-CHECKLIST.md`: review exact paths, run
relevant checks, create a signed local commit, push through authenticated HTTPS,
and verify the remote SHA. Use local `git` for commits and `gh` for HTTPS
authentication and remote checks. No SSH Git remote or force push.

The public mirror must not receive credentials, active secrets, local databases,
runtime output, or new NDA/client material. The remote already shares history
with the older `bridge-pimascor` repository, including previously committed
references. Changing this policy does not remove historical exposure; any
remediation requires a separate reviewed decision. See
`production-app/docs/REPOSITORY-EXPOSURE-AND-NDA.md`.

The pre-push hook allows only the portfolio HTTPS URL with
`PIMASCOR_ALLOW_PORTFOLIO_GITHUB_PUSH=1`. Check the path list and staged diff
before using that flag. Keep user changes outside the focused commit.
