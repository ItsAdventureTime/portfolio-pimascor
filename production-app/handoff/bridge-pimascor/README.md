# Bridge / PIMASCOR production handoff

This directory contains the client-facing handoff packet for the hosted
PIMASCOR production service. It is intentionally separate from the demo
materials and from the restricted deployment source.

For demo work, start with `../../docs/DEMO-DOCUMENTATION-INDEX.md`. The demo
runbook, demo Quadlets, synthetic reset, and demo source-of-truth are not in
this production handoff packet.

## Send to Bridge/PIMASCOR

Use `client-packet/` for the approved PDF packet and its manifest. The packet
covers product scope, requirements, workflows, API behavior, exports,
incidents, QA acceptance, Philippine controls, and the dynamic quotation
format reference.

The packet does not contain source code, Podman Quadlets, Caddy configuration,
Bash deployment scripts, credentials, production data, or secret values.

The generated ZIP archive and local review screenshots are not repository
artifacts. Keep them on an approved local or controlled transfer location only.

The PDFs under `client-packet/` are generated delivery snapshots. They are not
authoritative after their generation date; update the Markdown sources and
regenerate the packet before a new handoff.

## Keep with the VPS operator

The production deployment runbook remains in:

```text
production-app/docs/PRODUCTION-VPS-DEPLOYMENT.md
production-app/infra/
```

These files are operational references for the hosted service and should not
be placed in the ordinary client packet unless the support or source-transfer
agreement explicitly includes them.

## Acceptance record

Bridge should complete and sign the QA checklist in the client packet after
testing the live production route. Record the accepted release commit, date,
test account role, outcome, and responsible operator. Never record passwords,
OTP values, reset tokens, secret values, or full sensitive document contents.

The acceptance checklist is evidence to complete the handoff; its unchecked
items are not claims that the live VPS has already passed those tests.

## Account authority used by production

| Person | Email | Application role |
| --- | --- | --- |
| Marcelo Sabando | `processor1@pimascor.com` | Requester |
| Christian Arcangel | `processor2@pimascor.com` | Requester |
| Jaycee Dimandal | `processor3@pimascor.com` | Requester |
| Michelle Umpacuman | `operations@pimascor.com` | Bookkeeper/Mich |
| Carmel C. Urot | `carmel.urot@gmail.com` | GM |
| Atty. Daniel C. Subido | `dan.c.subido@gmail.com` | DCS / CEO / Chairman |

DCS/CEO/Chairman is one person represented by the technical `DCS` role. DCS
retains the approved emergency approval/override authority and must provide an
attributable reason for exceptional actions.

## Visual consistency

Production UI changes follow `docs/DESIGN-SYSTEM.md`, target WCAG 2.2 AA, and
are reviewed on desktop and mobile layouts. Each production visual change must
record equivalent guidance for the demo build so the two experiences remain
visually consistent while retaining their separate data and permissions.

## Revision control

The repository commit accepted during handoff must be written on the cover
sheet and matched against the private GitHub repository. Commits are signed
locally where the operator's Git signing key is configured; GitHub CLI is used
for remote authentication and verification checks.
