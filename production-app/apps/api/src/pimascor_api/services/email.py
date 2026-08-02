import json
import logging
from abc import ABC, abstractmethod
from html import escape
from urllib.parse import urlencode

import httpx

from ..config import Settings


logger = logging.getLogger("pimascor.email")


class EmailProvider(ABC):
    @abstractmethod
    def send_message(
        self,
        destination: str,
        subject: str,
        text: str,
        *,
        html: str | None = None,
        idempotency_key: str | None = None,
    ) -> None:
        raise NotImplementedError

    def send_login_code(
        self,
        destination: str,
        display_name: str,
        challenge_id: str,
        code: str,
        public_app_url: str,
        expires_in_minutes: int,
    ) -> None:
        base_url = public_app_url.rstrip("/") + "/"
        fragment = urlencode({"challenge": challenge_id, "code": code})
        sign_in_url = f"{base_url}#email-sign-in?{fragment}"
        safe_name = escape(display_name)
        safe_code = escape(code)
        safe_url = escape(sign_in_url, quote=True)
        text = (
            f"Hi {display_name},\n\n"
            "You’re signing in to PIMASCOR Operational Control. "
            "Use this code, or open the secure link below to finish signing in.\n\n"
            f"{code}\n\n"
            f"Verify and sign in: {sign_in_url}\n\n"
            f"This code works once and expires in {expires_in_minutes} minutes. "
            "If you didn’t try to sign in, you can ignore this email."
        )
        html = f"""<!doctype html>
<html lang="en">
<body style="margin:0;padding:0;background:#f4f6fb;color:#172033;font-family:Arial,'Helvetica Neue',sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#f4f6fb;">
    <tr>
      <td align="center" style="padding:28px 14px;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:560px;background:#ffffff;border:1px solid #dfe4ec;border-radius:18px;overflow:hidden;">
          <tr>
            <td style="padding:24px 28px;background:#14213d;color:#ffffff;">
              <div style="font-size:12px;font-weight:700;letter-spacing:1.5px;color:#e9d887;">PIMASCOR</div>
              <div style="margin-top:7px;font-size:23px;font-weight:700;line-height:1.25;">Finish signing in</div>
            </td>
          </tr>
          <tr>
            <td style="padding:28px;">
              <p style="margin:0 0 14px;font-size:16px;line-height:1.55;">Hi {safe_name},</p>
              <p style="margin:0 0 22px;font-size:16px;line-height:1.55;color:#4d5a70;">You’re signing in to PIMASCOR Operational Control. Use this code, or select the button below to finish signing in.</p>
              <div style="padding:18px 12px;text-align:center;background:#f8f0d2;border:1px solid #ead889;border-radius:12px;">
                <div style="margin-bottom:7px;font-size:11px;font-weight:700;letter-spacing:1.2px;color:#7a5a00;">YOUR SIGN-IN CODE</div>
                <div style="font-size:34px;font-weight:800;line-height:1.15;letter-spacing:8px;color:#14213d;">{safe_code}</div>
              </div>
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                <tr>
                  <td align="center" style="padding:22px 0 18px;">
                    <a href="{safe_url}" style="display:inline-block;padding:14px 22px;background:#1c2a4a;color:#ffffff;text-decoration:none;font-size:16px;font-weight:700;border-radius:10px;">Verify and sign in</a>
                  </td>
                </tr>
              </table>
              <p style="margin:0;font-size:14px;line-height:1.5;color:#647087;">This code works once and expires in {expires_in_minutes} minutes. If you didn’t try to sign in, you can ignore this email.</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
        self.send_message(
            destination,
            "Your PIMASCOR sign-in code",
            text,
            html=html,
            idempotency_key=f"login-code/{challenge_id}",
        )

    def send_activation_code(
        self,
        destination: str,
        display_name: str,
        challenge_id: str,
        code: str,
        public_app_url: str,
        expires_in_minutes: int,
    ) -> None:
        safe_name = escape(display_name)
        safe_code = escape(code)
        text = (
            f"Hi {display_name},\n\n"
            "Your PIMASCOR account is ready for activation. "
            "Use this one-time code to choose your password:\n\n"
            f"{code}\n\n"
            f"This code works once and expires in {expires_in_minutes} minutes. "
            "PIMASCOR will never email you a permanent password."
        )
        html = f"""<!doctype html>
<html lang="en">
<body style="margin:0;padding:0;background:#f4f6fb;color:#172033;font-family:Arial,'Helvetica Neue',sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#f4f6fb;">
    <tr><td align="center" style="padding:28px 14px;">
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:560px;background:#ffffff;border:1px solid #dfe4ec;border-radius:18px;overflow:hidden;">
        <tr><td style="padding:24px 28px;background:#14213d;color:#ffffff;">
          <div style="font-size:12px;font-weight:700;letter-spacing:1.5px;color:#e9d887;">PIMASCOR</div>
          <div style="margin-top:7px;font-size:23px;font-weight:700;line-height:1.25;">Activate your account</div>
        </td></tr>
        <tr><td style="padding:28px;">
          <p style="margin:0 0 14px;font-size:16px;line-height:1.55;">Hi {safe_name},</p>
          <p style="margin:0 0 22px;font-size:16px;line-height:1.55;color:#4d5a70;">Use this code to activate your PIMASCOR account, then choose a password in the app.</p>
          <div style="padding:18px 12px;text-align:center;background:#f8f0d2;border:1px solid #ead889;border-radius:12px;">
            <div style="margin-bottom:7px;font-size:11px;font-weight:700;letter-spacing:1.2px;color:#7a5a00;">YOUR ACTIVATION CODE</div>
            <div style="font-size:34px;font-weight:800;line-height:1.15;letter-spacing:8px;color:#14213d;">{safe_code}</div>
          </div>
          <p style="margin:22px 0 0;font-size:14px;line-height:1.5;color:#647087;">This code works once and expires in {expires_in_minutes} minutes. PIMASCOR will never email you a permanent password.</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""
        self.send_message(
            destination,
            "Activate your PIMASCOR account",
            text,
            html=html,
            idempotency_key=f"account-activation/{challenge_id}",
        )

    def send_password_reset(
        self,
        destination: str,
        display_name: str,
        challenge_id: str,
        token: str,
        public_app_url: str,
        expires_in_minutes: int,
    ) -> None:
        base_url = public_app_url.rstrip("/") + "/"
        fragment = urlencode({"challenge": challenge_id, "token": token})
        reset_url = f"{base_url}#password-reset?{fragment}"
        safe_name = escape(display_name)
        safe_url = escape(reset_url, quote=True)
        text = (
            f"Hi {display_name},\n\n"
            "We received a request to choose a new PIMASCOR password. "
            "Use the secure link below to continue.\n\n"
            f"Reset your password: {reset_url}\n\n"
            f"This link works once and expires in {expires_in_minutes} minutes. "
            "If you did not request this, you can ignore this email."
        )
        html = f"""<!doctype html>
<html lang="en">
<body style="margin:0;padding:0;background:#f4f6fb;color:#172033;font-family:Arial,'Helvetica Neue',sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#f4f6fb;">
    <tr><td align="center" style="padding:28px 14px;">
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:560px;background:#ffffff;border:1px solid #dfe4ec;border-radius:18px;overflow:hidden;">
        <tr><td style="padding:24px 28px;background:#14213d;color:#ffffff;">
          <div style="font-size:12px;font-weight:700;letter-spacing:1.5px;color:#e9d887;">PIMASCOR</div>
          <div style="margin-top:7px;font-size:23px;font-weight:700;line-height:1.25;">Reset your password</div>
        </td></tr>
        <tr><td style="padding:28px;">
          <p style="margin:0 0 14px;font-size:16px;line-height:1.55;">Hi {safe_name},</p>
          <p style="margin:0 0 22px;font-size:16px;line-height:1.55;color:#4d5a70;">Use the button below to choose a new password for your PIMASCOR account.</p>
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"><tr><td align="center" style="padding:4px 0 20px;">
            <a href="{safe_url}" style="display:inline-block;padding:14px 22px;background:#1c2a4a;color:#ffffff;text-decoration:none;font-size:16px;font-weight:700;border-radius:10px;">Choose a new password</a>
          </td></tr></table>
          <p style="margin:0;font-size:14px;line-height:1.5;color:#647087;">This link works once and expires in {expires_in_minutes} minutes. If you did not request this, you can ignore this email.</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""
        self.send_message(
            destination,
            "Reset your PIMASCOR password",
            text,
            html=html,
            idempotency_key=f"password-reset/{challenge_id}",
        )


class DevelopmentEmailProvider(EmailProvider):
    def send_message(
        self,
        destination: str,
        subject: str,
        text: str,
        *,
        html: str | None = None,
        idempotency_key: str | None = None,
    ) -> None:
        safe_text = "[password reset email content redacted]" if (idempotency_key or "").startswith("password-reset/") else text
        logger.warning(
            "Development email to %s | subject=%s | idempotency=%s | %s",
            destination,
            subject,
            idempotency_key or "none",
            safe_text,
        )


class ResendEmailProvider(EmailProvider):
    def __init__(self, settings: Settings):
        self.api_key = settings.resend_api_key_value
        self.from_address = settings.email_from_address

    def send_message(
        self,
        destination: str,
        subject: str,
        text: str,
        *,
        html: str | None = None,
        idempotency_key: str | None = None,
    ) -> None:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "pimascor-operations/0.2",
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        payload = {
            "from": self.from_address,
            "to": [destination],
            "subject": subject,
            "text": text,
        }
        if html:
            payload["html"] = html
        response = httpx.post(
            "https://api.resend.com/emails",
            headers=headers,
            content=json.dumps(payload),
            timeout=10,
        )
        response.raise_for_status()


class AzureEmailProvider(EmailProvider):
    def __init__(self, settings: Settings):
        if not settings.azure_email_endpoint:
            raise RuntimeError("Azure email endpoint is required")
        settings.azure_email_access_key_value
        self.settings = settings

    def send_message(
        self,
        destination: str,
        subject: str,
        text: str,
        *,
        html: str | None = None,
        idempotency_key: str | None = None,
    ) -> None:
        # Azure Communication Services uses signed requests. The adapter boundary is
        # intentionally present now; the official SDK is added when Azure is selected.
        raise RuntimeError(
            "Azure email is selected but its SDK adapter is not enabled yet; choose Resend or development"
        )


def get_email_provider(settings: Settings) -> EmailProvider:
    if settings.email_provider == "resend":
        return ResendEmailProvider(settings)
    if settings.email_provider == "azure":
        return AzureEmailProvider(settings)
    return DevelopmentEmailProvider()
