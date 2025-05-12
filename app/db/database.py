"""
 数据库模块
 
 该模块负责数据库连接和会话管理。
 使用SQLAlchemy ORM连接到OceanBase/MySQL数据库。
"""
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.core.config import get_settings, Settings

# Get settings instance
current_settings: Settings = get_settings()

# 构建MySQL/OceanBase数据库连接URL
SQLALCHEMY_DATABASE_URL = f"mysql+mysqlconnector://{current_settings.DB_USER}:{current_settings.DB_PASSWORD.get_secret_value()}@{current_settings.DB_HOST}:{current_settings.DB_PORT}/{current_settings.DB_NAME}"

# 创建MySQL引擎
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=False,  # 设置为True可打印SQL语句（调试用）
    pool_pre_ping=True,
    pool_recycle=1800  # 每小时回收一次连接 (3600秒) -> Changed to 30 minutes (1800 seconds)
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基础类用于ORM模型继承
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """
     数据库会话依赖函数
     
     该函数为FastAPI端点提供数据库会话，并确保请求结束后会话被关闭。
     用作FastAPI的依赖项注入。
     
     @return 生成器，产生数据库会话
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
