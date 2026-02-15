from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    debug_mode: bool = False

    db_user: str
    db_password: str
    db_name: str
    db_host: str
    db_port: int
    db_url: str = "sqlite:///:memory:"

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int

    llm_base_url: str = "http://localhost:8000/v1"
    llm_model: str

    max_tokens: int = 20
    model_temperature: float = 0.7

    open_ai_api_key: str = "EMPTY"


settings = Settings()
