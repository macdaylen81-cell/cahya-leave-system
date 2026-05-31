from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SECRET_KEY: str = "supersecretkey2026"

    # Database
    DATABASE_URL: str = ""

    # SMTP / Brevo
    SMTP_HOST: str = "smtp-relay.brevo.com"
    SMTP_PORT: int = 587

    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""

    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "Cahya Leave System"
    BREVO_API_KEY: str = ""

    # reCAPTCHA
    RECAPTCHA_SITE_KEY: str = ""
    RECAPTCHA_SECRET_KEY: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()