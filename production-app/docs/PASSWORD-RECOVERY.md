# PIMASCOR password recovery

This production feature lets an activated user recover access without an
Administrator seeing or setting the user's password. Pending first-login
accounts continue to use the activation flow.

## User flow

1. Select **Forgot password?** on the production sign-in page.
2. Submit the assigned username or email.
3. PIMASCOR shows the same confirmation whether the identifier is known,
   disabled, pending, unknown, or currently throttled.
4. If the account is eligible, Resend sends a single-use reset link.
5. Open the link, choose a password of at least 12 characters, and sign in
   again through the normal password-plus-email-code flow.

PIMASCOR does not email a permanent or generated password and does not
auto-sign-in after a reset. A successful reset revokes every existing session.

## Security controls

- Reset tokens use 48 bytes of cryptographically secure randomness and are
  stored only as SHA-256 hashes.
- Tokens are carried in a URL fragment, removed from the address bar before
  use, expire after 15 minutes, and are single-use.
- Five failed token attempts invalidate a request.
- Requests are persisted with hashed identifier/source values and limited to
  three per identifier and twenty per source in a rolling 60-minute window.
- Unknown identifiers still create a rate-limit ledger row, preventing an
  account-existence response difference.
- Email-provider failures are recorded for operators but retain the same
  non-disclosing response instead of becoming an account-existence oracle.
- Reset pages send `Referrer-Policy: no-referrer`; reset tokens are not query
  parameters and are not written to application/audit logs.
- The completion endpoint revokes existing sessions and records a
  privacy-minimized audit event without the token or password.

These controls follow the [OWASP Forgot Password Cheat
Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html),
[OWASP Authentication Cheat
Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html),
and [NIST SP 800-63B-4](https://pages.nist.gov/800-63-4/sp800-63b.html).

## API contract

```text
POST /api/v1/auth/password-reset/start
{ "identifier": "username-or-email" }

POST /api/v1/auth/password-reset/complete
{
  "challenge_id": "id-from-email-fragment",
  "token": "one-time-token-from-email-fragment",
  "password": "new-password",
  "confirmation": "new-password"
}
```

Hosted production responses never include the token. Development/test mode
may expose a development-only value so automated tests can exercise the flow;
never use that value as a production credential.

## Deployment checklist

The migration is `20260803_0013_password_reset_requests`. Build and transfer
the release locally, then run the normal production activation command with the
commit-matched artifact paths. No new Podman secret is required.

Local Mac command:

```bash
/Users/jk.deguzman/dev/bridge-ph_Dashboard/production-app/infra/scripts/deploy-production-vps.sh
```

VPS command after SSH login:

```bash
cd /var/home/jk/bridge-ph/pimascor/source && ./infra/scripts/update-production.sh --source /var/home/jk/bridge-ph/pimascor/source --api-image-archive /var/home/jk/bridge-ph/pimascor/release-artifacts/COMMIT/api-image.tar --web-dist /var/home/jk/bridge-ph/pimascor/release-artifacts/COMMIT/web-dist
```

Run `./infra/scripts/install-production-caddy.sh` only if the shared Caddy
configuration has not yet been activated for the production route.

## Acceptance evidence

Test active, disabled, pending, and unknown identifiers; confirm identical
generic responses. Use a real mailbox to verify delivery, fragment handling,
expiry, wrong-token lockout, single-use behavior, session revocation, and
normal re-authentication. Repeat on Chromium/Blink, Firefox/Gecko, and
Safari/WebKit desktop and mobile viewports.
