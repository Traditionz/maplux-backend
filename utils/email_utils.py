import os
from typing import List

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from jinja2 import Environment, select_autoescape, FileSystemLoader
from pydantic import NameEmail
from pydantic.main import BaseModel

from config import settings
from domain.user.schemas import UserBaseSchema
from exception.UserExceptions import SendActivationEmailException

env = Environment(
    loader=FileSystemLoader(f'{os.path.dirname(__file__)}/../templates/'),
    autoescape=select_autoescape(['html', 'xml'])
)


class EmailSchema(BaseModel):
    email: List[NameEmail]


class Email:

    def __init__(self, user: UserBaseSchema, url: str, email: List[NameEmail]):
        self.name = user.first_name
        self.sender = settings.email_from
        self.email = email
        self.url = url

    async def send_email(self, subject, template) -> None:

        conf = ConnectionConfig(
            MAIL_USERNAME=settings.email_username,
            MAIL_PASSWORD=settings.email_password,
            MAIL_FROM=settings.email_from,
            MAIL_PORT=settings.email_port,
            MAIL_SERVER=settings.email_server,
            MAIL_STARTTLS=False,
            MAIL_SSL_TLS=False,
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=True
        )

        template = env.get_template(f'{template}.html')

        html = template.render(
            url=self.url,
            first_name=self.name,
            subject=subject
        )

        msg = MessageSchema(
            subject=subject,
            recipients=self.email,
            body=html,
            subtype=MessageType.html,
        )
        fm = FastMail(conf)
        await fm.send_message(msg)

    async def send_activation_email(self):
        try:
            email_subject = f"Activate your {settings.app_name} account"
            await self.send_email(email_subject, 'email_activation')
        except Exception:

            raise SendActivationEmailException('Error sending activation email.')

    async def send_password_reset_email(self):
        try:
            email_subject = f"Password Reset - {settings.app_name}"
            await self.send_email(email_subject, 'reset_password')
        except Exception:

            raise SendActivationEmailException('Error sending password reset email.')
