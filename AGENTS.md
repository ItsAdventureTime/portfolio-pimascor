# Project agent boundary

## Active project material

Treat the current source tree, active documentation indexes, implementation
files, tests, deployment definitions, and Serena project memories as the
working source for this project.

## Archived material

Do not read, search, analyze, quote, or use files under `./not-needed/` unless
the user explicitly asks for a historical comparison or recovery. The folder
contains retired credentials, obsolete context prompts, historical prototypes,
and stale generated handoff snapshots. It is not project guidance.

When active documentation refers to archived material, treat that reference as
historical provenance only, never as a current requirement or implementation
authority.

## Documentation and Git synchronization

Keep Serena memories, authoritative documentation, code, tests, and deployment
guides synchronized. Use local Git for commits and the authenticated HTTPS
GitHub CLI workflow (`gh`) for remote authentication, push, and SHA checks. Do
not use an SSH Git remote for this project.
