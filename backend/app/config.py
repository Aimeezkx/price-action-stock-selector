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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
