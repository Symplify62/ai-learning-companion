"""
ASR服务工厂模块。
提供统一的ASR服务实例获取接口，便于后续扩展多种ASR实现。
"""

from app.core.config import Settings
from app.services.asr.base import AbstractAsrService
from app.services.xunfei_asr_service import XunfeiLfasrClient


def get_asr_service(settings: Settings) -> AbstractAsrService:
    """
    获取ASR服务实例的工厂方法。
    当前仅支持讯飞ASR实现，后续可扩展。

    Args:
        settings (Settings): 全局配置对象，需包含ASR服务相关配置。

    Returns:
        AbstractAsrService: 实现了ASR接口的服务实例。

    Raises:
        ValueError: 如果未正确配置讯飞ASR所需的APPID和SECRET_KEY。
    """
    # 检查讯飞ASR配置
    if settings.XUNFEI_APPID and settings.XUNFEI_SECRET_KEY:
        # 实例化并返回讯飞ASR客户端
        return XunfeiLfasrClient(
            appid=settings.XUNFEI_APPID,
            secret_key=settings.XUNFEI_SECRET_KEY
        )
    else:
        # 目前仅支持讯飞，未配置时报错
        raise ValueError("Xunfei ASR service is required but not configured with APPID and SECRET_KEY.")

    # TODO: 后续可根据settings或其他条件选择不同ASR服务实现 