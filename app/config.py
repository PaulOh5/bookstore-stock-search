from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    kakao_api_key: str = ""
    aladin_ttb_key: str = ""

    provider_timeout: float = 10.0
    search_cache_ttl: int = 86400  # 24 hours
    inventory_cache_ttl: int = 1800  # 30 minutes

    model_config = {"env_file": ".env"}


settings = Settings()
