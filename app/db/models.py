"""
 数据库ORM模型
 
 该模块定义了应用程序的SQLAlchemy ORM模型，对应数据库中的表结构。
"""
import uuid
import datetime
from sqlalchemy import Column, String, Text, Float, Boolean, Integer, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import JSON, LONGTEXT

from app.db.database import Base

def generate_uuid() -> str:
    """生成UUID字符串"""
    return str(uuid.uuid4())

class LearningSession(Base):
    """
     学习会话表模型
     
     对应数据库中的learning_sessions表
    """
    __tablename__ = "learning_sessions"
    
    session_id = Column(String(36), primary_key=True, index=True, default=generate_uuid)
    status = Column(String(50), nullable=False)
    user_id = Column(String(36), nullable=True, index=True)
    created_at = Column(String(50), default=lambda: datetime.datetime.now().isoformat())
    
    # 关系：一个会话可以有多个学习资源
    sources = relationship("LearningSource", back_populates="session")
    
    # 关系：一个会话可以有多个生成的笔记
    notes = relationship("GeneratedNote", back_populates="session")

    def __repr__(self):
        return f"<LearningSession(session_id='{self.session_id}', status='{self.status}')>"

class LearningSource(Base):
    """
     学习资源表模型
     
     对应数据库中的learning_sources表
    """
    __tablename__ = "learning_sources"
    
    video_id = Column(String(36), primary_key=True, index=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("learning_sessions.session_id"), nullable=False, index=True)
    user_id = Column(String(36), nullable=True, index=True)
    video_title = Column(String(255), nullable=False)
    video_description = Column(Text, nullable=True)
    source_description = Column(Text, nullable=True)
    total_duration_seconds = Column(Float, nullable=True)
    structured_transcript_segments_json = Column(LONGTEXT, nullable=True)
    extracted_key_information_json = Column(LONGTEXT, nullable=True)
    
    # 关系：多个学习资源关联到一个会话
    session = relationship("LearningSession", back_populates="sources")
    
    # 关系：一个学习资源可以有多个生成的笔记
    notes = relationship("GeneratedNote", back_populates="source")

    def __repr__(self):
        return f"<LearningSource(video_id='{self.video_id}', title='{self.video_title}')>"

class GeneratedNote(Base):
    """
     生成的笔记表模型
     
     对应数据库中的generated_notes表
    """
    __tablename__ = "generated_notes"
    
    note_id = Column(String(36), primary_key=True, index=True, default=generate_uuid)
    video_id = Column(String(36), ForeignKey("learning_sources.video_id"), nullable=False, index=True)
    session_id = Column(String(36), ForeignKey("learning_sessions.session_id"), nullable=False, index=True)
    user_id = Column(String(36), nullable=True, index=True)
    markdown_content = Column(LONGTEXT, nullable=False)
    is_user_edited = Column(Boolean, nullable=False, default=False)
    version = Column(String(10), nullable=False, default="1.0.0")
    created_at = Column(String(50), default=lambda: datetime.datetime.now().isoformat())
    last_modified_at = Column(String(50), default=lambda: datetime.datetime.now().isoformat())
    estimated_reading_time_seconds = Column(Integer, nullable=True)
    key_concepts_mentioned = Column(JSON, nullable=True)
    summary_of_note = Column(Text, nullable=True)
    
    # 关系：多个笔记关联到一个会话
    session = relationship("LearningSession", back_populates="notes")
    
    # 关系：多个笔记关联到一个学习资源
    source = relationship("LearningSource", back_populates="notes")
    
    # 关系：一个笔记可以有多个知识提示
    knowledge_cues = relationship("KnowledgeCue", back_populates="note")

    def __repr__(self):
        return f"<GeneratedNote(note_id='{self.note_id}', is_user_edited={self.is_user_edited})>"

class KnowledgeCue(Base):
    """
     知识提示表模型
     
     对应数据库中的knowledge_cues表
    """
    __tablename__ = "knowledge_cues"
    
    cue_id = Column(String(36), primary_key=True, index=True, default=generate_uuid)
    note_id = Column(String(36), ForeignKey("generated_notes.note_id"), nullable=False, index=True)
    question_text = Column(Text, nullable=False)
    answer_text = Column(Text, nullable=False)
    difficulty_level = Column(String(20), nullable=False)
    source_reference_in_note = Column(String(255), nullable=True)
    
    # 关系：多个知识提示关联到一个笔记
    note = relationship("GeneratedNote", back_populates="knowledge_cues")
    
    # 元数据
    created_at = Column(String(50), default=lambda: datetime.datetime.now().isoformat())
    last_modified_at = Column(String(50), default=lambda: datetime.datetime.now().isoformat())
    
    def __repr__(self):
        return f"<KnowledgeCue(cue_id='{self.cue_id}', difficulty_level='{self.difficulty_level}')>" 