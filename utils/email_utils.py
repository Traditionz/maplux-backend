from pathlib import Path

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel, EmailStr, NameEmail

from config import settings
from domain.user.models import User
from exception.UserExceptions import SendEmailException

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


class EmailSchema(BaseModel):
    email: list[NameEmail]


def name_email_for_user(user: User) -> NameEmail:
    parts = [part for part in (user.first_name, user.last_name) if part]
    display_name = " ".join(parts).strip()
    if not display_name:
        display_name = user.email.split("@")[0]
    return NameEmail(name=display_name, email=str(user.email))


def get_mail_config() -> ConnectionConfig:
    return ConnectionConfig(
        MAIL_USERNAME=settings.email_username,
        MAIL_PASSWORD=settings.email_password,
        MAIL_FROM=settings.email_from,
        MAIL_PORT=settings.email_port,
        MAIL_SERVER=settings.email_server,
        MAIL_STARTTLS=settings.email_starttls,
        MAIL_SSL_TLS=settings.email_ssl_tls,
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True,
    )


class Email:
    def __init__(self, user: User, url: str, email: list[NameEmail] | None = None):
        self.name = user.first_name
        self.sender: EmailStr = settings.email_from
        self.email = email if email is not None else [name_email_for_user(user)]
        self.url = url

    async def send_email(self, subject: str, template: str) -> None:
        conf = get_mail_config()
        html_template = env.get_template(f"{template}.html")
        html = html_template.render(
            url=self.url,
            first_name=self.name,
            subject=subject,
        )
        msg = MessageSchema(
            subject=subject,
            recipients=self.email,
            body=html,
            subtype=MessageType.html,
        )
        fm = FastMail(conf)
        await fm.send_message(msg)

    async def send_activation_email(self) -> None:
        try:
            email_subject = f"Activate your {settings.app_name} account"
            await self.send_email(email_subject, "email_activation")
        except Exception as exc:
            raise SendEmailException("Error sending activation email.") from exc

    async def send_password_reset_email(self) -> None:
        try:
            email_subject = f"Password Reset - {settings.app_name}"
            await self.send_email(email_subject, "reset_password")
        except Exception as exc:
            raise SendEmailException("Error sending password reset email.") from exc
