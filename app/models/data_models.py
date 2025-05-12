from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, HttpUrl
from app.core.enums import ProcessingStatus

class LearningSessionInput(BaseModel):
    """
     学习会话输入模型
     
     @param rawTranscriptText 原始文本转录
     @param initialVideoTitle 初始视频标题(可选)
     @param initialSourceDescription 初始源描述(可选)
     @param bilibili_video_url Bilibili视频URL(可选)
    """
    rawTranscriptText: Optional[str] = None
    initialVideoTitle: Optional[str] = None
    initialSourceDescription: Optional[str] = None
    bilibili_video_url: Optional[HttpUrl] = None

class LearningSessionResponse(BaseModel):
    """
     学习会话响应模型
     
     @param sessionId 会话ID
     @param status 会话状态
    """
    sessionId: str
    status: ProcessingStatus

class LearningSession(BaseModel):
    """
     学习会话完整模型
     
     @param session_id 会话ID
     @param status 会话状态
     @param user_id 用户ID(可选)
     @param created_at 创建时间
    """
    session_id: str
    status: ProcessingStatus
    user_id: Optional[str] = None
    created_at: datetime

class LearningSource(BaseModel):
    """
     学习资源模型
     
     @param video_id 视频ID
     @param session_id 会话ID
     @param user_id 用户ID(可选)
     @param video_title 视频标题
     @param video_description 视频描述(可选)
     @param source_description 资源描述(可选)
     @param total_duration_seconds 总时长(秒，可选)
     @param structured_transcript_segments_json 结构化转录片段JSON
     @param extracted_key_information_json 提取的关键信息JSON
    """
    video_id: str
    session_id: str
    user_id: Optional[str] = None
    video_title: str
    video_description: Optional[str] = None
    source_description: Optional[str] = None
    total_duration_seconds: Optional[float] = None
    structured_transcript_segments_json: str
    extracted_key_information_json: str

class GeneratedNote(BaseModel):
    """
     生成的笔记模型
     
     @param note_id 笔记ID
     @param video_id 视频ID
     @param session_id 会话ID
     @param user_id 用户ID(可选)
     @param markdown_content Markdown内容
     @param is_user_edited 是否被用户编辑
     @param version 版本
     @param created_at 创建时间
     @param last_modified_at 最后修改时间
     @param estimated_reading_time_seconds 预计阅读时间(秒，可选)
     @param key_concepts_mentioned 提及的关键概念(可选)
     @param summary_of_note 笔记摘要(可选)
    """
    note_id: str
    video_id: str
    session_id: str
    user_id: Optional[str] = None
    markdown_content: str
    is_user_edited: bool = False
    version: str = "1.0.0"
    created_at: datetime
    last_modified_at: datetime
    estimated_reading_time_seconds: Optional[int] = None
    key_concepts_mentioned: Optional[List[str]] = None
    summary_of_note: Optional[str] = None

class KnowledgeCue(BaseModel):
    """
     知识提示模型
     
     @param cue_id 提示ID
     @param note_id 笔记ID
     @param question_text 问题文本
     @param answer_text 答案文本
     @param difficulty_level 难度级别
     @param source_reference_in_note 笔记中的源引用(可选)
    """
    cue_id: str
    note_id: str
    question_text: str
    answer_text: str
    difficulty_level: str
    source_reference_in_note: Optional[str] = None

# --- New/Updated Models for API Read Operations ---

class KnowledgeCueRead(BaseModel):
    """Pydantic model for reading KnowledgeCue data."""
    model_config = {'from_attributes': True}

    cue_id: str
    note_id: str
    question_text: str
    answer_text: str
    difficulty_level: str
    source_reference_in_note: Optional[str] = None

class GeneratedNoteRead(BaseModel):
    """Pydantic model for reading GeneratedNote data."""
    model_config = {'from_attributes': True}

    note_id: str
    video_id: str
    session_id: str
    user_id: Optional[str] = None
    markdown_content: str
    is_user_edited: bool
    version: str
    created_at: datetime
    last_modified_at: datetime
    estimated_reading_time_seconds: Optional[int] = None
    key_concepts_mentioned: Optional[List[str]] = None
    summary_of_note: Optional[str] = None

class NoteWithCues(GeneratedNoteRead):
    """GeneratedNoteRead model extended with its associated knowledge cues."""
    knowledge_cues: List[KnowledgeCueRead] = []

class FinalResultsPayload(BaseModel):
    """Payload containing all notes with their cues for a session."""
    notes: List[NoteWithCues] = []
    plain_transcript_text: Optional[str] = None
    timestamped_transcript_segments: Optional[List[Dict[str, Any]]] = None
    ai_generated_video_title: Optional[str] = None

class LearningSessionDetail(BaseModel):
    """Detailed Pydantic model for a learning session, potentially including final results."""
    model_config = {'from_attributes': True}

    session_id: str
    status: ProcessingStatus
    user_id: Optional[str] = None
    created_at: datetime
    final_results: Optional[FinalResultsPayload] = None
