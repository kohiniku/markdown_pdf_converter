from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config import settings

# Build engine for current backend (disable thread check for SQLite)
# 接続先に応じたエンジンを生成する（SQLiteではスレッドチェックを無効化）
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

# Session factory used per request
# リクエスト単位でセッションを発行するファクトリ
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base shared by models
# モデルで共有するベースクラス
Base = declarative_base()

def get_db():
    # Database session used via FastAPI dependency injection
    # FastAPIの依存性注入で利用するデータベースセッション
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
