import os
from typing import List

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from jinja2 import Environment, select_autoescape, FileSystemLoader
from pydantic import EmailStr
from pydantic.main import BaseModel

from config import env_vars
from domain.user.schemas import UserBase
from exception.UserExceptions import SendActivationEmailException

env = Environment(
    loader=FileSystemLoader(f'{os.path.dirname(__file__)}/../templates/'),
    autoescape=select_autoescape(['html', 'xml'])
)


class EmailSchema(BaseModel):
    email: List[EmailStr]


class Email:

    def __init__(self, user: UserBase, url: str, email: List[EmailStr]):
        self.name = user.first_name
        self.sender = env_vars.EMAIL_FROM
        self.email = email
        self.url = url

    async def send_email(self, subject, template) -> None:

        conf = ConnectionConfig(
            MAIL_USERNAME=env_vars.EMAIL_USERNAME,
            MAIL_PASSWORD=env_vars.EMAIL_PASSWORD,
            MAIL_FROM=env_vars.EMAIL_FROM,
            MAIL_PORT=env_vars.EMAIL_PORT,
            MAIL_SERVER=env_vars.EMAIL_SERVER,
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
            email_subject = f"Activate your {env_vars.APP_NAME} account"
            await self.send_email(email_subject, 'email_activation')
        except Exception:

            raise SendActivationEmailException('Error sending activation email.')

    async def send_password_reset_email(self):
        try:
            email_subject = f"Password Reset - {env_vars.APP_NAME}"
            await self.send_email(email_subject, 'reset_password')
        except Exception:

            raise SendActivationEmailException('Error sending password reset email.')
