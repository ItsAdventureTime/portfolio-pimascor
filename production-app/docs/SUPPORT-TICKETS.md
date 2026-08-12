# Support tickets and owner messages

## Secure support portal (current)

Support tickets are durable records in PostgreSQL. Each production ticket
creates three separate capability links: one for the requester, one labelled
`Support Staff` for JK, and one labelled `Bridge Admin` for Alyssa
(`alyssa.d@bridge-ph.com`). The links are sent by Resend to the requester and
the two support recipients. They do not require an application login.

The raw token is generated with high entropy, stored only as a SHA-256 hash,
expires after the configured portal TTL, is revoked when a replacement link is
issued, and is accepted through `X-Support-Token`. Email links place the token
in the URL fragment; the web app removes it from browser history immediately.
Do not copy a capability link into a ticket, log, screenshot, analytics event,
or chat. The API responds with `Referrer-Policy: no-referrer`.
Portal attachment responses are private and sent with `Cache-Control: no-store`.

The portal supports Markdown text, a guided category/reason decision tree,
five attachments per message, and 25 MB per attachment. Production accepts
PDF, JPEG, PNG, WebP, TXT, Markdown, and CSV files after extension and magic
signature validation. Attachment bytes use the private production Backblaze
B2 prefix `support-tickets/`; generated object keys never use the original
filename. Attachments are marked deleted and removed from B2 when a ticket is
closed. A maintenance pass retries any failed object deletion.

Support can assign a ticket to `Support Staff` or `Bridge Admin`, mark it
`Resolved`, or mark it `Closed`. Opening a new ticket from a support link moves
it from `Open` to `In progress`. Tickets with no update for seven days are
closed by the API maintenance task with an apology email to the requester.

The demo uses the same portal contract, but attachment rows and replies are
explicitly simulated, no production email is sent, and simulated attachments
are not downloadable. Because there is no demo email, the authenticated
create response exposes a demo-only simulated `portal_url` and the dialog
offers an **Open simulated no-login thread** action. Production never exposes
raw portal URLs through its API. Demo and production each apply the same
forward migration to their own database; they never share a database or reset
path.

## API portal routes

```text
GET  /support-tickets/portal/{ticket_id}
POST /support-tickets/portal/{ticket_id}/replies
POST /support-tickets/portal/{ticket_id}/assignment
POST /support-tickets/portal/{ticket_id}/status
GET  /support-tickets/portal/attachments/{attachment_id}
```

The authenticated routes remain available for the signed-in workspace. The
portal routes require only the recipient-specific capability token. All
portal writes are version-checked and audited.

This document defines the shared support-message contract for production and
demo. It is a user-facing support workflow, not the application incident
reporting path. Incident reporting remains for detected application failures;
support tickets cover questions, suggestions, and ordinary help requests.

## Shared UI behavior

- Support is opened from the persistent **Support** action in the workspace
  top bar. It is not a full-page destination or a primary navigation item.
- Desktop uses a compact centered dialog. Mobile uses the same responsive
  dialog at near-full width with touch-sized controls and a scrollable ticket
  list.
- Ticket details and the conversation stay inside the same dialog. Users can
  return to their ticket list without opening a second full-height panel.
- The dialog has clear labels, keeps background interaction inactive, traps
  keyboard focus, closes with `Escape`, and returns focus to the Support action.

## Production behavior

- Any authenticated user can submit a support message from the Support dialog.
- The API creates a durable ticket with a unique human-readable ticket number,
  subject, message, requester, role, deployment tier, timestamps, status, and
  audit history.
- Admin-level users can assign, respond, change status, and add internal notes.
  Requesters can view their own tickets and replies.
- Production notifications go to Alyssa (`alyssa.d@bridge-ph.com`) and JK
  (`jk@delegateops.business`) for new tickets and responses. Email contains the
  ticket number and safe context, never passwords, OTPs, sessions, secrets,
  full bank details, or uploaded documents.
- Email failure does not lose the ticket. Delivery outcome is recorded and can
  be retried by an authorized Admin.

## Demo behavior

- Demo exposes the same Support dialog, form, ticket number, status, and reply
  presentation using synthetic records.
- Demo replies are simulated and clearly labeled; a submitted demo ticket
  receives a synthetic response and demo users may add follow-up messages.
  The authenticated demo create response provides a synthetic portal link so
  the no-login thread can be exercised without an email. Demo never sends
  production email or writes to production storage.
- The daily reset removes demo tickets, replies, and ticket audit events.

## Suggested state model

```text
Open -> In progress -> Waiting for requester -> Resolved -> Closed
                  \-> Resolved -> Open (Admin reopens)
```

Messages and replies remain append-only. Closing a ticket does not delete it.

## Security and accessibility

Support messages are untrusted user input. The API must validate length,
authorization, CSRF, concurrency, and output encoding. The UI must provide
keyboard-accessible fields, clear labels, confirmation feedback, and a visible
ticket number after submission. Support messages are not a channel for secrets
or confidential document uploads.

## Acceptance evidence

Production acceptance must demonstrate ticket creation, unique numbering,
Admin assignment/reply/status changes, requester visibility restrictions,
email delivery or safe failure handling, audit history, and retry behavior.
Demo acceptance must demonstrate the same path with simulated replies and no
production email or storage side effects.
