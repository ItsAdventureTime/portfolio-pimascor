# PIMASCOR user-facing release notes

This is the user-facing record of production changes. It explains what users
can do now and how the change helps their work; it intentionally leaves out
implementation details.

## 2026-08-10 — A more dependable return after maintenance

- **Improved — Get back to work with confidence.** PIMASCOR now confirms the
  workspace is ready before an update is reported as complete, reducing the
  chance of a short-lived connection error immediately after maintenance.
- **Improved — Keep the workspace available.** The sign-in and workspace
  route are checked together, so users can return to the same protected
  workflow once the update is ready.

## 2026-08-09 — Clearer recovery visibility

- **Improved — Keep recovery controlled.** Restoring production data remains a
  deliberate owner-led CLI process with a dry run and quarantine review first;
  no web action can replace live records accidentally.

## 2026-08-03 — A smoother way to stay on top of every shipment

PIMASCOR is easier to keep close, easier to recover, and clearer to use when
work moves from one team to the next.

- **New — Install PIMASCOR as an app.** After signing in, add PIMASCOR to a
  phone or computer Home Screen for one-tap access and a focused workspace.
  The reminder stays out of the sign-in form and disappears when PIMASCOR is
  already running as an installed app.
- **New — Reset your password yourself.** Use **Forgot password?** to receive
  a secure email link and get back to work without waiting for an
  administrator.
- **Improved — Move through work with more confidence.** Important workflow
  decisions, document access, and security messages are presented more clearly
  so the next step is easier to find.
- **Improved — Sign in faster on a phone.** On narrow screens, the sign-in form
  appears before the supporting brand story, so users can authenticate without
  scrolling through the full introduction first.

Each production release has a date and release ID. The latest update appears
once after a user signs in following that release. Selecting **Continue to
workspace** or closing the dialog records that the user has seen it; the same
update does not return on later logins when the acknowledgement is saved. A
temporary save failure never blocks the workspace and the update returns on a
later login so it can be acknowledged again.

## Release-writing standard

Future entries should:

- lead with the user benefit and workflow impact;
- use plain, conversational language and short paragraphs;
- label items **New**, **Improved**, **Updated**, or **Removed**;
- include the release date and avoid internal ticket, code, infrastructure,
  or deployment terminology;
- describe any action the user needs to take, without making the announcement
  a technical manual.

The in-app announcement uses the same release entry and is presented as an
accessible, keyboard-friendly dialog. It does not interrupt the sign-in form;
it appears after authentication and can be acknowledged before continuing. The
dialog closes immediately when the user continues, while the acknowledgement
is saved in the background.
