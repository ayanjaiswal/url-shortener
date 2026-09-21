from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "url-shortener"
    database_url: str = "postgresql://shortener:shortener@localhost:5432/shortener"
    redis_url: str = "redis://localhost:6379/0"


settings = Settings()
