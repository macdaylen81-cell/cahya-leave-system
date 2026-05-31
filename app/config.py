from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SECRET_KEY: str = "supersecretkey2026"
    
    # PostgreSQL Connection
    DATABASE_URL: str = ""   # Leave empty, use environment variable
    
    # Email Settings
    SMTP_SENDER: str = ""
    SMTP_PASSWORD: str = ""
    
    RECAPTCHA_SITE_KEY: str = ""
    RECAPTCHA_SECRET_KEY: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()