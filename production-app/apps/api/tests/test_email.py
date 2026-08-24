import json

from pimascor_api.config import Settings
from pimascor_api.services.email import EmailProvider, ResendEmailProvider


class FakeResponse:
    def raise_for_status(self):
        return None


def test_resend_uses_user_agent_and_idempotency_key(monkeypatch, tmp_path):
    secret = tmp_path / "resend"
    secret.write_text("re_example", encoding="utf-8")
    settings = Settings(
        email_provider="resend",
        resend_api_key_file=secret,
        email_from_address="PIMASCOR <no-reply@delegateops.business>",
    )
    captured = {}

    def fake_post(url, *, headers, content, timeout):
        captured.update(
            url=url,
            headers=headers,
            content=json.loads(content),
            timeout=timeout,
        )
        return FakeResponse()

    monkeypatch.setattr("pimascor_api.services.email.httpx.post", fake_post)
    ResendEmailProvider(settings).send_message(
        "admin@example.com",
        "Incident",
        "Safe context",
        idempotency_key="incident-admin/example",
    )
    assert captured["url"] == "https://api.resend.com/emails"
    assert captured["headers"]["User-Agent"] == "pimascor-operations/0.2"
    assert captured["headers"]["Idempotency-Key"] == "incident-admin/example"
    assert captured["content"]["to"] == ["admin@example.com"]
    assert captured["content"]["text"] == "Safe context"


class CapturingEmailProvider(EmailProvider):
    def __init__(self):
        self.message = {}

    def send_message(
        self,
        destination,
        subject,
        text,
        *,
        html=None,
        idempotency_key=None,
    ):
        self.message = {
            "destination": destination,
            "subject": subject,
            "text": text,
            "html": html,
            "idempotency_key": idempotency_key,
        }


def test_login_email_is_personal_clear_and_uses_fragment_for_secret():
    provider = CapturingEmailProvider()
    provider.send_login_code(
        "alyssa@example.com",
        "Alyssa & Team",
        "challenge-123",
        "482915",
    "https://delegateops.business/demo/pimascor/",
        5,
    )

    message = provider.message
    assert message["destination"] == "alyssa@example.com"
    assert "Hi Alyssa & Team" in message["text"]
    assert "\n482915\n" in message["text"]
    assert "expires in 5 minutes" in message["text"]
    assert "/?challenge=" not in message["text"]
    assert "#email-sign-in?challenge=challenge-123&code=482915" in message["text"]
    assert "font-size:34px" in message["html"]
    assert "Alyssa &amp; Team" in message["html"]
    assert "<img" not in message["html"]
    assert message["idempotency_key"] == "login-code/challenge-123"
