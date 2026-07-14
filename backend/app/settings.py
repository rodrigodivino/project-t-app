from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://study:study@localhost:5433/study"
    access_code: str = "dev"

    model_config = {"env_file": ".env"}


settings = Settings()
