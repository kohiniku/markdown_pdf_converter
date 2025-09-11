from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Any
import os, json

class Settings(BaseSettings):
    database_url: str = "sqlite:///./app.db"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int | None = None
    cors_origins: List[str] = []
    
    upload_dir: str = "uploads"
    output_dir: str = "output"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    
    pdf_engine: str = "weasyprint"
    pdf_timeout: int = 30
    newline_as_space: bool = False
    
    secret_key: str = "your-secret-key-here"
    access_token_expire_minutes: int = 30

    class Config:
        # Load from backend/.env (pydantic will let real env override .env)
        env_file = ".env"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> Any:
        """Accept JSON list or comma-separated string for CORS_ORIGINS."""
        if isinstance(v, str):
            s = v.strip()
            if s.startswith("["):
                try:
                    return json.loads(s)
                except Exception:
                    pass
            return [item.strip() for item in s.split(",") if item.strip()]
        return v

settings = Settings()
