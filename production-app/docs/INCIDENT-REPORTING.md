# Incident detection and recovery

This is the shared baseline for demo and production. It applies to every signed-in role.

## User experience

Routine action results, status updates, form validation, and expected workflow
warnings use the centered feedback dialog documented in `DESIGN-SYSTEM.md`. They are
not incidents and never create an incident record, audit event, or email. Only a
detected application failure offers **Report for investigation**.

When an operation fails, the app:

1. explains what happened in plain language;
2. suggests a safe next step;
3. states that nothing has been sent;
4. offers **Dismiss**, which closes the message and does nothing else; and
5. offers **Report for investigation**, which privately informs Bridge PH Admin
   and the Developer, then closes after both deliveries are confirmed.

A server failure tells the user to check the relevant list before repeating an
accounting, payment, or recording action because the browser may not know whether
the transaction finished. If report delivery fails, the dialog stays open so the
user may retry or dismiss it.

## Reports and privacy

Client and browser errors create no incident, audit event, or email when dismissed.
Selecting **Report for investigation** creates an immutable incident and audit event.
An unexpected server failure keeps a protected technical reference for diagnostics,
but does not email anyone until the user explicitly reports it.

Two separate Resend emails are attempted:

- `alyssa.d@bridge-ph.com`: plain operational and accounting context;
- `jk@delegateops.business`: safe technical context, correlation ID, reproduction
  information, and a ready-to-copy Codex investigation prompt.

Reports include the actor, role, operation, page, time, error code, deployment tier,
safe browser-engine label, and correlation ID. They exclude passwords, email codes,
session values, secrets, full bank details, documents, form values, and screenshots.
Resend idempotency keys prevent duplicate sends during safe retries.

## API

```text
POST /api/v1/incidents
POST /api/v1/incidents/{incident-id}/report
```

Both endpoints require a signed-in session and CSRF protection. A client-generated
UUID and provider idempotency keys make retries safe. A user can report their own
client incident or the protected server reference returned to their browser.

Expected HTTP and form errors return a stable code, plain message, recovery
suggestion, and correlation ID. Browser API, runtime, and fatal render errors use
the same explicit-consent rule.

## Configuration

Non-secret recipient settings stay in the API `.container` file:

```ini
Environment=INCIDENT_EMAIL_ENABLED=true
Environment=INCIDENT_ADMIN_EMAIL=alyssa.d@bridge-ph.com
Environment=INCIDENT_DEVELOPER_EMAIL=jk@delegateops.business
```

The Resend API key remains a Podman secret. Demo and production must use distinct
database, email, storage, and container credentials even though they share this code.

## Demo cleanup

After the revised API is deployed, this guarded command deletes only demo incident
reports and their incident audit events:

```bash
podman exec bridge-ph-pimascor-demo-api python -m pimascor_api.incident_admin purge --confirm DELETE-DEMO-INCIDENTS
```

It refuses to run when `DEPLOYMENT_TIER` is not `demo`. It does not delete users,
business records, documents, Podman secrets, unrelated audit events, journald logs,
or emails that Resend has already accepted.

## Design and security basis

- [W3C Alert Dialog Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/alertdialog/)
- [W3C Modal Dialog Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/)
- [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)
- [Resend idempotency keys](https://resend.com/docs/dashboard/emails/idempotency-keys)
- [Resend API authentication and User-Agent requirement](https://resend.com/docs/api-reference/introduction)
- [OpenAI ChatGPT prompting guidance](https://learn.chatgpt.com/docs/prompting)
