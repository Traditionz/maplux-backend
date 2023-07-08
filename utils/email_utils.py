import os
import traceback
from typing import List

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from jinja2 import Environment, select_autoescape, FileSystemLoader
from pydantic import EmailStr
from pydantic.main import BaseModel

from config import env_vars
from domain.user.schemas import UserBase

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
        #try:
        await self.send_email('Activate your Maplux account', 'email_activation')

        traceback.print_exc()
        #except Exception as e:

            #raise SendActivationEmailException('Error sending activation email.')
