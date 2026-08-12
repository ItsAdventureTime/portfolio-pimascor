# Support tickets and owner messages

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
  Demo never sends production email or writes to production storage.
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
