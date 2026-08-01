# Bridge / PIMASCOR operational handoff

This document defines the handoff of the hosted PIMASCOR production service to
Bridge. It is an operational handoff, not a transfer of secrets through email
or chat. It assumes the application remains hosted on the existing Fedora CoreOS
VPS and that Bridge is the client and operational owner after acceptance.

## 1. Handoff boundary

The day-to-day service is already deployed at:

```text
https://delegateops.business/pimascor/
```

The production runtime facts are:

| Area | Location or service |
| --- | --- |
| Production data, PostgreSQL data, uploads, backup staging | `~/bridge-ph/pimascor` on the VPS |
| Rootless Podman Quadlets | `~/.config/containers/systemd/bridge-ph/pimascor` |
| Shared edge proxy | Rootless Caddy user service |
| Public route | `delegateops.business/pimascor/` |
| Object storage | Private Backblaze B2 bucket and production prefix configured in the VPS secrets |
| Transactional email | Resend account configured in the VPS secrets |
| Encrypted backups | Restic repository configured in the VPS secrets and backup timers |

Routine users do not need the source tree, Python, Node.js, npm, PostgreSQL,
Restic, AWS CLI, or B2 CLI on their computers. They use the HTTPS application.
VPS operators use the production runbook and rootless `systemctl --user` and
Podman commands.

## 2. Files for the operational handoff

Send Bridge a read-only PDF or archive containing these documents and reference
files. Confirm that the version/commit is recorded on the handoff cover sheet.

### Required

- `docs/PRODUCTION-VPS-DEPLOYMENT.md` — production paths, roles, secrets,
  deployment sequence, Caddy activation, backup, export, and recovery notes.
- `docs/PRODUCT-SPEC.md` — product scope and supported capabilities.
- `docs/REQUIREMENTS-V2.md` — approved requirements and business rules.
- `docs/USER-FLOWS.md` — role-based workflows for acceptance testing.
- `docs/API-CONTRACT.md` — supported API behavior for integrations and support.
- `docs/DATA-EXPORTS.md` — archive contents, retention, and export controls.
- `docs/INCIDENT-REPORTING.md` — user reporting and operator response behavior.
- `docs/QUALITY-ASSURANCE.md` — release and browser/device acceptance criteria.
- `docs/UX-PHILIPPINE-CONTROLS.md` — language, currency, and PH-context controls.
- `docs/reference/AAA_FORMAT_QUOTATION_revised.pdf` — quotation/contract layout
  reference used for dynamic print output.
- `infra/caddy/pimascor-production.handlers.Caddyfile` — production-only Caddy
  handlers, if Bridge will maintain the existing Caddy instance.

The demo runbook and demo Quadlets are not production operating instructions.
Do not include `docs/DEMO-VPS-DEPLOYMENT.md` in the production operator packet
unless it is clearly labelled as a separate non-production environment.

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
- GM and DCS payment authority/override rules match the approved policy.
- Quotation print preview and generated PDF dynamically populate client,
  shipment, currency, amount, terms, and dates using the revised reference.
- Authorized users can open quotation and uploaded document attachments;
  unauthorized users receive the expected denial.
- CSV accounting export and full archive export produce the documented formats.
- Export retention, one-hour download availability, and weekly request limit are
  confirmed with non-production test data.
- PostgreSQL dump, Restic backup, and a restoration test are evidenced.
- Resend operational and technical incident notifications reach the agreed
  recipients without exposing confidential payloads.
- Desktop and mobile acceptance is completed in Chromium, WebKit, and Gecko.

Acceptance is incomplete until Bridge signs the operational checklist and names
the person responsible for incident response and backup restoration.

## 6. First 24 hours after acceptance

Bridge should:

1. Confirm the owner and backup operator can log in through separate accounts.
2. Rotate any credential that was temporarily shared during commissioning.
3. Verify the VPS firewall, DNS, TLS renewal, Caddy service, and rootless user
   lingering are still enabled.
4. Run one controlled backup and verify that the Restic repository can list and
   restore a test object.
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

The source code is intentionally excluded from the operational packet because
the service is hosted on the existing VPS. If Bridge's contract transfers the
source/IP, perform a separate recorded transfer:

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
