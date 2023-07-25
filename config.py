from pydantic import BaseSettings


class EnvVars(BaseSettings):
    CLIENT_ORIGIN: str

    API_PREFIX: str

    DATABASE_URL: str

    ACTIVATE_SECRET_KEY: str
    ACTIVATE_SALT: str

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str

    EMAIL_USERNAME: str
    EMAIL_PASSWORD: str
    EMAIL_FROM: str
    EMAIL_PORT: int
    EMAIL_SERVER: str

    class Config:
        env_file = './.env'


env_vars = EnvVars()
