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
    pdf_base_font_size: int = 13
    # Page setup defaults
    pdf_page_size_default: str = "A4"
    pdf_page_orientation_default: str = "portrait"  # portrait | landscape
    pdf_page_margin_default: str = "12mm"           # CSS length (uniform)
    
    # Proxy settings (optional)
    http_proxy: str | None = None
    https_proxy: str | None = None
    no_proxy: str | None = None
    apply_proxy_on_startup: bool = True

    # Targeted GROWI compatibility version (documentation only)
    growi_target_version: str = "7.3.0"

    # Manual page break rules
    manual_break_enabled_default: bool = False
    # Comma-separated list or JSON array of exact phrases that trigger a page break
    manual_break_tokens: List[str] = []
    
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

    @field_validator("manual_break_tokens", mode="before")
    @classmethod
    def parse_break_tokens(cls, v: Any) -> Any:
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return []
            if s.startswith("["):
                try:
                    return json.loads(s)
                except Exception:
                    pass
            return [item.strip() for item in s.split(",") if item.strip()]
        return v

settings = Settings()

def apply_proxy_settings():
    """Apply proxy-related environment variables if configured.

    This makes downstream libraries (e.g., HTTP clients, WeasyPrint URL fetcher)
    respect corporate proxies. Set values to empty to clear.
    """
    mapping = {
        "HTTP_PROXY": settings.http_proxy,
        "http_proxy": settings.http_proxy,
        "HTTPS_PROXY": settings.https_proxy,
        "https_proxy": settings.https_proxy,
        "NO_PROXY": settings.no_proxy,
        "no_proxy": settings.no_proxy,
    }
    for k, v in mapping.items():
        if v is None:
            continue
        if v == "":
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
