from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


_BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    postgres_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/styleforge_db"
    jwt_secret: str = "your-super-secret-jwt-key"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_pass: Optional[str] = None
    smtp_from: Optional[str] = None

    daily_image_quota: int = 20

    # Ollama / local VLM settings
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3.5:9b"
    ollama_timeout: int = 420          # seconds to wait for model response

    # Long-running GenAI proxy/backend calls (5-7 minutes)
    genai_request_timeout: int = 420

    # Credit system costs
    new_user_credits: int = 100        # credits granted to a brand-new user
    style_critique_credits: int = 5    # credits deducted per style critique
    image_generation_credits: int = 10 # credits deducted per image generation
    fabric_simulation_credits: int = 5 # credits deducted per fabric simulation

    auth_service_url: str = "http://localhost:8001"
    catalog_service_url: str = "http://localhost:8002"
    analytics_service_url: str = "http://localhost:8004"
    audit_service_url: str = "http://localhost:8005"
    genai_service_url: str = "http://localhost:8006"

    model_config = SettingsConfigDict(
        env_file=_BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
