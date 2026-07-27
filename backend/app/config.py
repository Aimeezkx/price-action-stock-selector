from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Price Action Stock Selector"
    database_url: str = "sqlite:///./price_action.db"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    seed_demo_data: bool = True

    ibkr_host: str = "127.0.0.1"
    ibkr_port: int = 7497
    ibkr_client_id: int = 17
    ibkr_readonly: bool = True
    ibkr_market_data_type: int = 3
    ibkr_request_delay_seconds: float = 0.35

    market_sync_enabled: bool = True
    market_sync_timezone: str = "America/Chicago"
    market_sync_hour: int = 15
    market_sync_minute: int = 0
    market_bar_retention: int = 300

    email_digest_enabled: bool = False
    email_digest_hour: int = 15
    email_digest_minute: int = 30
    email_digest_recipient: str = "zkxaimee0914@gmail.com"
    email_digest_min_score: float = 60
    email_digest_target_r: float = 2
    email_smtp_host: str = "smtp.gmail.com"
    email_smtp_port: int = 587
    email_smtp_username: str = ""
    email_smtp_password: str = ""
    email_smtp_from: str = ""
    email_smtp_starttls: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def email_digest_recipients(self) -> list[str]:
        return [
            item.strip()
            for item in self.email_digest_recipient.split(",")
            if item.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
