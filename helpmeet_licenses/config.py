from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    jwt_secret: str
    admin_api_key: str

    model_config = {"env_file": ".env"}


settings = Settings()
