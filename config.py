from pydantic import EmailStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Core app settings ───────────────────────────────────────
    app_name: str
    client_origin: str
    api_prefix: str = "/api"
    testing: bool = False

    # ── Database ────────────────────────────────────────────────
    database_url: str

    # ── Security ────────────────────────────────────────────────
    activate_secret_key: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    cookie_secure: bool = False
    cookie_samesite: str = "lax"

    # ── Email ───────────────────────────────────────────────────
    email_username: str
    email_password: str
    email_from: EmailStr
    email_port: int = 587
    email_server: str = "smtp.gmail.com"
    email_starttls: bool = True
    email_ssl_tls: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("jwt_algorithm")
    @classmethod
    def validate_jwt_algorithm(cls, value: str) -> str:
        allowed = {"HS256", "HS384", "HS512"}
        if value not in allowed:
            raise ValueError(f"jwt_algorithm must be one of {sorted(allowed)}.")
        return value

    @field_validator("cookie_samesite")
    @classmethod
    def validate_cookie_samesite(cls, value: str) -> str:
        normalized = value.lower()
        allowed = {"lax", "strict", "none"}
        if normalized not in allowed:
            raise ValueError(f"cookie_samesite must be one of {sorted(allowed)}.")
        return normalized


settings = Settings()
