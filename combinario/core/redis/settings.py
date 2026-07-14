from pydantic import RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    debug_mode: bool = False

    redis_host: str
    redis_port: int
    redis_db: int
    redis_password: str = ""
    redis_url: RedisDsn


redis_settings = RedisSettings()
