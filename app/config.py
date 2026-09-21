from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "url-shortener"
    database_url: str = "postgresql+psycopg://shortener:shortener@localhost:5432/shortener"
    redis_url: str = "redis://localhost:6379/0"
    base_url: str = "http://localhost:8000"

    # No default on purpose: the app refuses to start without a real secret.
    secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60


settings = Settings()  # pyright: ignore[reportCallIssue]
