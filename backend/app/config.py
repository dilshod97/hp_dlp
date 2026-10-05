"""Sozlamalar — .env fayldan o'qiladi."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./hp_dlp.db"
    agent_api_key: str = "dev-agent-key-change-me"
    secret_key: str = "dev-secret-change-me"          # token imzolash uchun
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
    media_dir: str = "./media"
    # Birinchi ishga tushishda yaratiladigan standart admin
    admin_username: str = "admin"
    admin_password: str = "admin123"

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
