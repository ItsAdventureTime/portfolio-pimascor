# Bridge / PIMASCOR operational handoff

## Current deployment lifecycle

The current deploy scripts build, transfer, and automatically activate both
demo and production releases in one command. New deployments do not create
rollback images, previous web directories, production backup timers, retention
units, or restore helpers. Existing remote backup data and secrets are kept;
the production updater only disables and removes the exact repository-managed
backup unit/helper paths.

This document defines the handoff of the hosted PIMASCOR production service to
Bridge. It is an operational handoff, not a transfer of secrets through email
or chat. It assumes the application remains hosted on the existing Fedora CoreOS
VPS and that Bridge is the client and operational owner after acceptance.

## 1. Handoff boundary

The day-to-day service is already deployed at:

```text
https://delegateops.business/prod/pimascor/
```

The production runtime facts are:

| Area | Location or service |
| --- | --- |
| Production data, PostgreSQL data, uploads, backup staging | `~/bridge-ph/pimascor` on the VPS |
| Rootless service definitions | `~/.config/containers/systemd/bridge-ph/pimascor` |
| Shared edge proxy | Rootless Caddy user service |
| Public route | `delegateops.business/prod/pimascor/` |
| Object storage | Private Backblaze B2 bucket and production prefix configured in the VPS secrets |
| Transactional email | Resend account configured in the VPS secrets |
| Encrypted backups | Restic repository configured in the VPS secrets and backup timers |

Routine users do not need the source tree, Python, Node.js, npm, PostgreSQL,
Restic, AWS CLI, or B2 CLI on their computers. They use the HTTPS application.
Authorized operators use the restricted technical runbook for host maintenance.

## 2. Files for the client handoff

The official client-facing deliverable is
`handoff/bridge-pimascor/client-packet/00-pimascor-production-handoff-guide.pdf`.
Send Bridge this read-only PDF through an approved secure channel. It is a
plain-language guide for PIMASCOR's non-technical users and includes the
current workflow, account activation, downloads, backups, support, failure
handling, and acceptance steps. Confirm that the version/commit is recorded on
the handoff cover sheet.

The Markdown documents below are the internal source and review set used to
prepare the client guide. They are not an ordinary client packet. Disclose
them only when the agreed support or source-transfer scope requires it.

### Internal source and review set

- `docs/PRODUCT-SPEC.md` — product scope and supported capabilities.
- `docs/REQUIREMENTS-V2.md` — approved requirements and business rules.
- `docs/USER-FLOWS.md` — role-based workflows for acceptance testing.
- `docs/API-CONTRACT.md` — supported API behavior for integrations and support.
- `docs/DATA-EXPORTS.md` — archive contents, retention, and export controls.
- `docs/PRODUCTION-BACKUP-RESTORE-RUNBOOK.md` — owner-only backup/restore
  responsibilities and evidence (technical appendix; no secret values).
- `docs/INCIDENT-REPORTING.md` — user reporting and operator response behavior.
- `docs/QUALITY-ASSURANCE.md` — release and browser/device acceptance criteria.
- `docs/UX-PHILIPPINE-CONTROLS.md` — language, currency, and PH-context controls.
- `docs/reference/AAA_FORMAT_QUOTATION_revised.pdf` — quotation/contract layout
  reference used for dynamic print output.

The client packet intentionally excludes Podman Quadlets, Caddyfiles, Bash
scripts, deployment scripts, and source code. Those are operator/developer
materials, not user-facing handoff documents. The restricted technical
runbook, `docs/PRODUCTION-VPS-DEPLOYMENT.md`, remains with the VPS operator and
can be disclosed later under an agreed support scope.

The demo runbook and demo Quadlets are not production operating instructions and
must not be included in this client packet.

## 3. Access and ownership transfer

Transfer access through the provider's invitation or an approved password
manager. Never place values in the handoff archive.

Transfer or document the owner and backup owner for:

1. VPS account and rootless service account `jk` (or a newly created Bridge
   operator account).
2. DNS and domain registrar for `delegateops.business`.
3. CDN account and purge controls, if a CDN is used in front of the VPS.
4. Backblaze B2 account, private bucket, application keys, and lifecycle rules.
5. Resend account, sending domain, API key, and verified sender identity.
6. GitHub private repository and organization/team access, if the source/IP
   transfer is included in the contract.
7. Password manager vault containing production secrets and the Restic password.

Create named Bridge accounts where supported. Do not hand over a shared
personal login. Require MFA, least privilege, and an emergency recovery owner.

## 4. Never send in the ordinary handoff archive

Do not email, paste, or commit any of the following:

- Podman secret values, B2 application keys, Resend API keys, Restic password,
  database passwords, or session/CSRF secrets.
- VPS SSH private keys, GitHub tokens, CDN tokens, DNS tokens, or password-reset
  links.
- A plaintext `.env` file or shell history containing credentials.
- A production PostgreSQL dump, upload archive, or Restic repository unless
  Bridge explicitly requests it and the transfer is encrypted, access-limited,
  logged, and covered by the data-processing agreement.
- OTP codes, user passwords, browser cookies, or active session exports.

Production attachments and accounting records may contain personal or sensitive
information. Treat any data copy as a controlled disclosure, not as a software
artifact.

## 5. Acceptance session with Bridge

Record evidence for each item below, including date, operator, build commit, and
the account used. Do not record passwords or full document contents.

- HTTPS route and API health endpoint respond successfully.
- Admin can see and manage the documented accounts, including Mich.
- First-login email OTP and password activation work for a test account.
- Activated users can request a password reset, receive a single-use expiring
  link, choose a new password, and sign in again; old sessions are revoked.
- Unknown, disabled, pending, expired, reused, and rate-limited reset requests
  do not disclose account existence or expose reset tokens in logs.
- GM can approve or return work but cannot act in DCS for Payment. DCS/CEO/
  Chairman owns ordinary DCS Payment actions and the emergency/contingency
  override of a GM-owned approval, with an attributable reason.
- Quotation print preview and generated PDF dynamically populate client,
  shipment, currency, amount, terms, and dates using the revised reference.
- Authorized users can open quotation and uploaded document attachments;
  unauthorized users receive the expected denial.
- CSV accounting export and full archive export produce the documented formats.
- Export retention, one-hour download availability, and weekly request limit are
  confirmed with non-production test data.
- PostgreSQL dump and encrypted Restic backup are evidenced. Restore authority
  remains with the named service owner and is CLI-only; Admin and DCS can view
  the in-app backup catalog but cannot restore or replace production data.
- Resend operational and technical incident notifications reach the agreed
  recipients without exposing confidential payloads.
- Desktop and mobile acceptance is completed in Chromium, WebKit, and Gecko.
- A dated **What's new in PIMASCOR** announcement appears once for a user after
  a release, records acknowledgement, and does not repeat on the next login.

Acceptance is incomplete until Bridge signs the operational checklist and names
the person responsible for incident response and backup restoration.

## 6. First 24 hours after acceptance

Bridge should:

1. Confirm the owner and backup operator can log in through separate accounts.
2. Rotate any credential that was temporarily shared during commissioning.
3. Verify the VPS firewall, DNS, TLS renewal, Caddy service, and rootless user
   lingering are still enabled.
4. Run one controlled backup, verify the encrypted catalog entry, list Restic
   snapshots, and complete a dry-run followed by a quarantine restore. Do not
   restore directly over the live production root.
5. Confirm the production B2 bucket is private and the production prefix is
   separate from demo objects.
6. Confirm the data-retention, incident-response, and data-subject request
   contacts under Bridge/PIMASCOR's privacy governance.

After the agreed support window, revoke the developer's SSH, cloud, email,
CDN, DNS, and repository access unless a written support agreement requires it.

## 7. Governance basis

This handoff uses a least-privilege, evidence-based transfer model. CIS Controls
v8.1 recommends prioritizing foundational safeguards through Implementation Group
1 and measuring them; NIST SP 800-61 Rev. 3 treats incident response as part of
the wider CSF 2.0 risk-management lifecycle. For Philippine operations, the
National Privacy Commission's Data Privacy Act guidance requires reasonable and
appropriate organizational, physical, and technical safeguards and requires
third-party processors to implement appropriate protections.

These references guide the operational checklist; they do not replace Bridge's
contract, data-processing agreement, privacy notices, retention policy, or legal
review.

## 8. Source and intellectual-property transfer

The initial client handoff does not include source code. The hosted service can
be used without a local source checkout, compiler, or build environment. If
PIMASCOR or Bridge later wants the complete source/IP package, it requires a
separate purchase and written transfer agreement with you; it is not included
automatically in this operational handoff.

If that separate source/IP purchase is approved, perform a recorded transfer:

- grant Bridge access to the private GitHub repository or deliver an encrypted
  repository archive;
- include the exact release commit accepted in Section 5;
- include the complete source, migrations, tests, infrastructure definitions,
  reference PDFs, and build metadata required by the contract;
- transfer repository ownership or establish the agreed maintainer model;
- rotate deploy keys, CI tokens, signing keys, and personal access tokens after
  the transfer;
- keep the operational handoff free of production secrets and live personal data.

Ownership, license, warranty, support period, and liability terms should be
confirmed in writing by the parties; this document is not legal advice.
