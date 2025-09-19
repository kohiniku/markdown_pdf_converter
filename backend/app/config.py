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
    # Default page setup values
    # ページ設定のデフォルト値
    pdf_page_size_default: str = "A4"
    pdf_page_orientation_default: str = "portrait"  # portrait | landscape
    pdf_page_margin_default: str = "12mm"           # CSS length (uniform)
    
    # Optional proxy-related settings
    # プロキシ関連の設定（任意）
    http_proxy: str | None = None
    https_proxy: str | None = None
    no_proxy: str | None = None
    apply_proxy_on_startup: bool = True

    # Target GROWI compatibility version (for documentation)
    # 目標とするGROWI互換バージョン（ドキュメント用）
    growi_target_version: str = "7.3.0"

    secret_key: str = "your-secret-key-here"
    access_token_expire_minutes: int = 30

    class Config:
        # Load from backend/.env while allowing real environment overrides
        # backend/.envから読み込みつつ環境変数の上書きを許可する
        env_file = ".env"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> Any:
        """Normalize CORS_ORIGINS from JSON or comma-separated strings.
        CORS_ORIGINSをJSON文字列またはカンマ区切り文字列として扱えるように整形する。
        """
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

def apply_proxy_settings():
    """Apply configured proxy values to environment variables.

    Ensure HTTP clients and WeasyPrint respect corporate proxies; remove keys when empty.
    設定済みのプロキシ情報を環境変数へ適用し、HTTPクライアントやWeasyPrintが企業プロキシを利用できるようにする。空文字が指定された場合は該当キーを削除して無効化する。
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
