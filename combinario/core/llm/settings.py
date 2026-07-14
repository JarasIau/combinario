from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    debug_mode: bool = False

    llm_base_url: str
    llm_model: str

    max_tokens: int
    model_temperature: float

    open_ai_api_key: str


llm_settings = LLMSettings()
