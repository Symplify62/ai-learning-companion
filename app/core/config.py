"""
 配置模块
 
 该模块定义了应用程序的配置设置，包括数据库连接参数。
 使用Pydantic的BaseSettings从环境变量加载配置。
"""
import os
import functools
from pydantic import SecretStr
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# 加载.env文件中的环境变量（如果存在）
load_dotenv()

class Settings(BaseSettings):
    """
     应用程序设置类
     
     @param DB_HOST 数据库主机（OceanBase/MySQL）
     @param DB_PORT 数据库端口
     @param DB_USER 数据库用户名
     @param DB_PASSWORD 数据库密码（使用SecretStr保护）
     @param DB_NAME 数据库名称
     @param GOOGLE_API_KEY 用于Gemini API的API密钥（使用SecretStr保护）
     @param XUNFEI_APPID 讯飞开放平台语音识别API凭证 (可选)
     @param XUNFEI_SECRET_KEY 讯飞开放平台语音识别API凭证 (可选)
    """
    # 数据库连接设置（全部为必填项）
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASSWORD: SecretStr
    DB_NAME: str
    GOOGLE_API_KEY: SecretStr

    # 讯飞开放平台语音识别API凭证 (可选)
    XUNFEI_APPID: str | None = None
    XUNFEI_SECRET_KEY: str | None = None
    
    class Config:
        """Pydantic配置类"""
        env_file = ".env"
        case_sensitive = True
        extra = 'ignore'

@functools.lru_cache()
def get_settings() -> Settings:
    return Settings()

# settings = Settings() 