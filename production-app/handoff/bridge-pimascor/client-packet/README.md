# Generated client packet

This directory contains the current client-facing production handoff for
PIMASCOR.

## Official deliverable

- `00-pimascor-production-handoff-guide.pdf`

The guide is a single 16-page A4 PDF written in English (US). It explains the
hosted service in plain language, including the user workflow, first-time
account activation and login, downloads, backups, support, failure handling,
and acceptance steps.

The cover includes the supplied Bridge Consulting and PIMASCOR branding. The
guide is intended for PIMASCOR's non-technical users and does not include
source code, infrastructure files, credentials, operator identities,
infrastructure IP addresses, or live production data.

The hosted service includes encrypted production backups. Admin and DCS can
review backup completion status in the application; restoration is not a web
feature and remains restricted to the named service owner through a
dry-run-first VPS CLI procedure.

## Delivery controls

Use `DELIVERY-MANIFEST.txt` to confirm the PDF hash and packet revision before
delivery. A ZIP file may be used as a transfer wrapper, but it must contain
only the approved PDF unless the manifest is updated.

Update the authoritative Markdown documents under `production-app/docs/`
before regenerating the PDF. Keep the production handoff separate from the
demo documentation and from the restricted deployment runbook.
