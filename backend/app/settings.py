from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    access_code: str = "dev"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
