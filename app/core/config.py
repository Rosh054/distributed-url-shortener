from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "distributed-url-shortener"
    log_level: str = "INFO"
    environment: str = "local"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    database_url: str = "postgresql://shortuser:shortpass@localhost:5432/shortdb"
    redis_url: str = "redis://localhost:6379/0"

    base_url: str = "http://localhost:8000"
    short_code_length: int = 7
    cache_ttl_seconds: int = 3600
    cache_key_prefix: str = "url:cache:"

    redis_click_queue_key: str = "clicks:queue"
    worker_poll_timeout: int = 5
    worker_max_retries: int = 3
    worker_base_backoff_seconds: float = 1.0

    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60

    ip_hash_salt: str = "local-dev-salt"


settings = Settings()
