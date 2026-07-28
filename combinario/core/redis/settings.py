from arq.connections import RedisSettings as ArqRedisSettings
from pydantic_settings import BaseSettings, SettingsConfigDict


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    redis_host: str
    redis_port: int
    redis_db: int
    redis_password: str = ""

    def as_arq_settings(self) -> ArqRedisSettings:
        return ArqRedisSettings(
            host=self.redis_host,
            port=self.redis_port,
            database=self.redis_db,
            password=self.redis_password or None,
        )


redis_settings = RedisSettings()
