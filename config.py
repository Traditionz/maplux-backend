from pydantic import EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Core app settings ───────────────────────────────────────
    app_name: str
    client_origin: str
    api_prefix: str = "/api"

    # ── Database ────────────────────────────────────────────────
    database_url: str

    # ── Security ────────────────────────────────────────────────
    activate_secret_key: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"

    # ── Email ───────────────────────────────────────────────────
    email_username: str
    email_password: str
    email_from: EmailStr
    email_port: int = 587
    email_server: str = "smtp.gmail.com"

    model_config = SettingsConfigDict(
        env_file=".env",  # relative to project root or absolute path
        env_file_encoding="utf-8",
        case_sensitive=False,  # very useful
        extra="ignore",  # ignore unknown env vars
        # env_prefix="MYAPP_"         # optional prefix if you want
    )


settings = Settings()
