from types import SimpleNamespace

import pytest
from pydantic import NameEmail

from exception.UserExceptions import SendEmailException
from utils.email_utils import Email, EmailSchema, get_mail_config, name_email_for_user


def test_name_email_for_user_uses_full_name():
    user = SimpleNamespace(first_name="John", last_name="Doe", email="john@example.com")
    named = name_email_for_user(user)
    assert named.name == "John Doe"
    assert named.email == "john@example.com"
    assert str(named) == "John Doe <john@example.com>"


def test_name_email_for_user_infers_local_part():
    user = SimpleNamespace(first_name="", last_name="", email="only@example.com")
    named = name_email_for_user(user)
    assert named.name == "only"
    assert named.email == "only@example.com"


def test_email_schema_accepts_name_email():
    schema = EmailSchema(email=[NameEmail("Ada Lovelace", "ada@example.com")])
    assert schema.email[0].name == "Ada Lovelace"


def test_get_mail_config_uses_starttls():
    conf = get_mail_config()
    assert conf.MAIL_STARTTLS is True
    assert conf.MAIL_SSL_TLS is False


@pytest.mark.asyncio
async def test_send_activation_and_reset_email(monkeypatch):
    sent = []

    class FakeFastMail:
        def __init__(self, conf):
            self.conf = conf

        async def send_message(self, message):
            sent.append(message)

    monkeypatch.setattr("utils.email_utils.FastMail", FakeFastMail)
    user = SimpleNamespace(first_name="John", last_name="Doe", email="john@example.com")
    email = Email(user, "http://example.com/activate")
    await email.send_activation_email()
    await email.send_password_reset_email()
    assert len(sent) == 2
    assert "Activate" in sent[0].subject
    assert "Password Reset" in sent[1].subject


@pytest.mark.asyncio
async def test_send_email_failures(monkeypatch):
    class BoomFastMail:
        def __init__(self, conf):
            pass

        async def send_message(self, message):
            raise RuntimeError("smtp failed")

    monkeypatch.setattr("utils.email_utils.FastMail", BoomFastMail)
    user = SimpleNamespace(first_name="John", last_name="Doe", email="john@example.com")
    email = Email(
        user,
        "http://example.com/activate",
        email=[NameEmail("John", "john@example.com")],
    )
    with pytest.raises(SendEmailException, match="activation"):
        await email.send_activation_email()
    with pytest.raises(SendEmailException, match="password reset"):
        await email.send_password_reset_email()


