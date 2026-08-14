# Bridge / PIMASCOR production handoff

This directory contains the client-facing handoff packet for the hosted
PIMASCOR production service. It is intentionally separate from the demo
materials and from the restricted deployment source.

For demo work, start with `../../docs/DEMO-DOCUMENTATION-INDEX.md`. The demo
runbook, demo Quadlets, synthetic reset, and demo source-of-truth are not in
this production handoff packet.

## Send to Bridge/PIMASCOR

Use `client-packet/00-pimascor-production-handoff-guide.pdf` as the official
client-facing guide. It is a single 16-page PDF written in English (US) for
PIMASCOR's non-technical users. It covers product behavior, workflows,
first-time account activation, downloads, backups, support, failure handling,
and acceptance steps.

The packet does not contain source code, Podman Quadlets, Caddy configuration,
Bash deployment scripts, credentials, production data, or secret values.

An optional ZIP file is only a transfer wrapper. It must contain the approved
PDF and no other files unless the delivery manifest is updated first. Local
review screenshots are not repository artifacts.

The approved PDF includes both Bridge Consulting and PIMASCOR branding. It is
the current delivery artifact for this handoff and is tracked with the
manifest in `client-packet/`.

## Delivery communication

Use `BRIDGE-TEAM-MESSAGE.md` when notifying the Bridge Team. The message asks
the team to review the guide before sending questions and to reserve replies
for items the guide does not answer or that appear inaccurate or incomplete.

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
| Marcelo Sabando | `processor1@pimascor.com` | Processor / Requester |
| Christian Arcangel | `processor2@pimascor.com` | Processor / Requester |
| Jaycee Dimandal | `processor3@pimascor.com` | Processor / Requester |
| Michelle Umpacuman | `operations@pimascor.com` | Bookkeeper/Mich |
| Carmel C. Urot | `carmel.urot@gmail.com` | GM |
| Atty. Daniel C. Subido | `dan.c.subido@gmail.com` | DCS / CEO / Chairman |

Bridge Accounting is a separate business label mapped to the Admin capability
set until a distinct technical role is approved. Both Processor/Requester and
Bridge Accounting may view their permitted own-shipment profitability data;
Admin-level Bridge Accounting access includes all-shipment profitability.

DCS/CEO/Chairman is one person represented by the technical `DCS` role. DCS
retains the approved emergency approval/override authority and must provide an
attributable reason for exceptional actions.

## Visual consistency

Production UI changes follow `docs/DESIGN-SYSTEM.md`, target WCAG 2.2 AA, and
are reviewed on desktop and mobile layouts. Each production visual change must
record equivalent guidance for the demo build so the two experiences remain
visually consistent while retaining their separate data and permissions.

## Revision control

The current packet revision is 2026-08-14.

The repository commit accepted during handoff must be written on the cover
sheet and matched against the private GitHub repository. Commits are signed
locally where the operator's Git signing key is configured; GitHub CLI is used
for remote authentication and verification checks.
