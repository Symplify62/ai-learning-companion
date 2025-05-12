"""
ASR 服务抽象基类

该模块定义了 ASR（自动语音识别）服务的抽象接口。
所有具体的 ASR 服务实现都应该继承这个基类。
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class AbstractAsrService(ABC):
    """
    ASR 服务的抽象基类
    
    定义了 ASR 服务必须实现的接口。
    所有具体的 ASR 服务实现都应该继承这个类并实现其抽象方法。
    """
    
    @abstractmethod
    async def transcribe(self, audio_file_path: str) -> Optional[List[Dict[str, Any]]]:
        """
        异步转录指定的音频文件

        Args:
            audio_file_path: 要转录的音频文件的路径

        Returns:
            如果转录成功，返回一个片段字典列表，
            每个字典代表一个识别的语音片段
            (例如，包含 'text', 'start_time_ms', 'end_time_ms', 'speaker' 等键)。
            如果转录失败或没有识别到任何片段，返回 None。
        """
        pass 