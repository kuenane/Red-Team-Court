from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://redteam:redteam@db:5432/redteam"

    # Qwen via DashScope's OpenAI-compatible endpoint
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    qwen_model: str = "qwen-plus"          # swap for "qwen3.5-plus" / "qwen3.6-plus" as available

    max_upload_chars: int = 60_000         # truncate very large docs before sending to agents
    debate_top_n_per_agent: int = 3        # findings per agent carried into debate

    class Config:
        env_file = ".env"


settings = Settings()
