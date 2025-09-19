from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.sql import func
from app.database import Base

class ConversionHistory(Base):
    """Table storing Markdown-to-PDF conversion history.
    Markdown→PDF変換の履歴を保持するテーブル。
    """
    __tablename__ = "conversion_history"
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(String, unique=True, index=True)
    original_filename = Column(String)
    output_filename = Column(String)
    file_size = Column(Integer)
    conversion_time = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String, default="completed")
    error_message = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    
class Settings(Base):
    """Key-value table for application-specific settings.
    アプリ固有の設定値を保存するキーバリューテーブル。
    """
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    value = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
