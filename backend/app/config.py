from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://stockpredict:stockpredict@localhost:5432/stockpredict"
    app_version: str = "0.1.0"


settings = Settings()
