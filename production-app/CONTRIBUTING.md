# Contributing

## Scope

This repository contains the deployable PIMASCOR application, its operational documentation, and its deployment definitions. Do not add credentials, local databases, uploaded documents, production exports, or real personal or financial data.

## Evidence discipline

Follow `docs/FACTUAL-BASIS.md`. Separate owner-confirmed facts, repository
configuration, command output, external references, inferences, and unknowns.
Do not state that a VPS action completed without its command output, and do not
invent a path, service state, provider configuration, or production decision.

## Local workflow

1. Start from `main` and create one short-lived branch per focused change, such as `feat/client-payment-filter` or `fix/demo-reset-health-check`.
2. Keep commits small and use an imperative Conventional Commit-style subject, for example `fix(api): reject invalid payment allocation`.
3. Before committing an API change, create or refresh the pinned development
   environment with `uv sync --extra dev`, then run `uv run pytest` from
   `apps/api`; run Ruff when it is available. Commit the generated `uv.lock`
   whenever dependency resolution is available, rather than relying on an
   unpinned local environment.
4. Before committing a web change, run `npm run build` from `apps/web`.
5. Before committing infrastructure or security changes, review the diff and the relevant deployment/runbook documentation together.

## Commit and release policy

- Never rewrite published `main` history or move a release tag.
- This project uses the private GitHub remote `git@github.com:ItsAdventureTime/bridge-pimascor.git`.
- Every change that modifies tracked files must be committed locally and pushed to that private remote after local validation. Never push to an unverified remote, and never use force-push.
- Tag an accepted release only after the demo or production validation evidence is recorded.
- Treat secrets, personal data, live finance records, and production exports as incident-sensitive: do not commit them. If one is committed, stop distribution, rotate the affected secret or access, and use an approved remediation process rather than casually rewriting history.
- For every demo-relevant change handoff, provide the exact one-line local
  transfer command and exact one-line VPS activation command from
  `docs/DEMO-VPS-DEPLOYMENT.md`, plus the checks that actually passed. Keep
  local validation distinct from VPS activation evidence.
- Do not describe a release as production-ready until the role, responsive, and
  browser-engine checks in `docs/QUALITY-ASSURANCE.md` are recorded.

## Private hosted-repository controls

Keep the GitHub repository private. Where GitHub repository settings are used,
configure a `main` ruleset that blocks force-pushes, requires passing checks and
review, and protects workflow/security configuration with CODEOWNERS.
