"""
 数据访问层（CRUD操作）
 
 该模块提供数据库CRUD（创建、读取、更新、删除）操作函数。
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.core.enums import ProcessingStatus

from . import models as db_models
from app.models import data_models as pydantic_models

def create_learning_session(
    db: Session, 
    status: ProcessingStatus,
    user_id: Optional[str] = None
) -> db_models.LearningSession:
    """
     创建新的学习会话记录
     
     @param db 数据库会话
     @param status 会话状态
     @param user_id 用户ID（可选）
     @return 创建的学习会话数据库模型实例
    """
    db_session = db_models.LearningSession(
        status=status.value,
        user_id=user_id
        # session_id将由默认UUID函数自动生成
        # created_at将由默认func.now()自动生成
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

def create_learning_source(
    db: Session, 
    session_id: str, 
    video_title: str, 
    user_id: Optional[str] = None, 
    initial_source_description: Optional[str] = None
) -> db_models.LearningSource:
    """
     创建新的学习资源记录
     
     @param db 数据库会话
     @param session_id 会话ID
     @param video_title 视频标题
     @param user_id 用户ID（可选）
     @param initial_source_description 初始资源描述（可选）
     @return 创建的学习资源数据库模型实例
    """
    # 如果视频标题为空，使用占位符
    # 实际的AI生成标题将在后续由Module A.1生成
    db_source = db_models.LearningSource(
        session_id=session_id,
        video_title=video_title if video_title else "Untitled Video - Pending AI Processing",  # 确保video_title不为空
        source_description=initial_source_description,
        user_id=user_id
        # video_id将由默认UUID函数自动生成
        # 其他字段如video_description和JSON字段初始为null/默认值
    )
    db.add(db_source)
    db.commit()
    db.refresh(db_source)
    return db_source

def create_generated_note(
    db: Session,
    video_id: str,
    session_id: str,
    note_markdown_content: str,
    estimated_reading_time_seconds: Optional[int],
    key_concepts_mentioned: Optional[List[str]],
    summary_of_note: Optional[str],
    user_id: Optional[str] = None
) -> db_models.GeneratedNote:
    """
     创建生成的笔记记录
     
     @param db 数据库会话
     @param video_id 视频ID
     @param session_id 会话ID
     @param note_markdown_content 笔记Markdown内容
     @param estimated_reading_time_seconds 预计阅读时间（秒）
     @param key_concepts_mentioned 提及的关键概念列表
     @param summary_of_note 笔记摘要
     @param user_id 用户ID（可选）
     @return 创建的笔记数据库模型实例
    """
    # 直接将列表或None传递给模型
    db_note = db_models.GeneratedNote(
        video_id=video_id,
        session_id=session_id,
        markdown_content=note_markdown_content,
        estimated_reading_time_seconds=estimated_reading_time_seconds,
        key_concepts_mentioned=key_concepts_mentioned,
        summary_of_note=summary_of_note,
        user_id=user_id
        # note_id将由默认UUID函数自动生成
        # is_user_edited默认为False
        # version默认为"1.0.0"
        # created_at和last_modified_at将由默认func.now()自动生成
    )
    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    return db_note

def create_knowledge_cue(
    db: Session,
    note_id: str,
    question_text: str,
    answer_text: str,
    difficulty_level: str,
    source_reference_in_note: Optional[str] = None
) -> db_models.KnowledgeCue:
    """
     创建知识提示记录
     
     @param db 数据库会话
     @param note_id 笔记ID
     @param question_text 问题文本
     @param answer_text 答案文本
     @param difficulty_level 难度级别
     @param source_reference_in_note 笔记中的源引用（可选）
     @return 创建的知识提示数据库模型实例
    """
    # 创建知识提示记录
    db_cue = db_models.KnowledgeCue(
        note_id=note_id,
        question_text=question_text,
        answer_text=answer_text,
        difficulty_level=difficulty_level,
        source_reference_in_note=source_reference_in_note
        # cue_id将由默认UUID函数自动生成
        # created_at和last_modified_at将由默认func.now()自动生成
    )
    db.add(db_cue)
    db.commit()
    db.refresh(db_cue)
    return db_cue

def get_learning_session(
    db: Session, 
    session_id: str
) -> Optional[db_models.LearningSession]:
    """
     根据ID获取学习会话
     
     @param db 数据库会话
     @param session_id 会话ID
     @return 学习会话数据库模型实例，如果不存在则返回None
    """
    return db.query(db_models.LearningSession).filter(db_models.LearningSession.session_id == session_id).first()

def get_learning_sources_by_session(
    db: Session, 
    session_id: str
) -> List[db_models.LearningSource]:
    """
     获取会话关联的所有学习资源
     
     @param db 数据库会话
     @param session_id 会话ID
     @return 学习资源数据库模型实例列表
    """
    return db.query(db_models.LearningSource).filter(db_models.LearningSource.session_id == session_id).all()

def get_learning_source_by_session_id(
    db: Session, 
    session_id: str
) -> Optional[db_models.LearningSource]:
    """
     获取与会话关联的单个学习资源
     
     从与指定会话ID关联的学习资源中获取第一个记录。
     在当前MVP中，一个会话通常只有一个主要的学习资源。
     
     @param db 数据库会话
     @param session_id 会话ID
     @return 学习资源数据库模型实例，如果不存在则返回None
    """
    return db.query(db_models.LearningSource).filter(db_models.LearningSource.session_id == session_id).first()

def get_notes_by_session_id(
    db: Session,
    session_id: str
) -> List[db_models.GeneratedNote]:
    """
     获取与会话关联的所有生成笔记
     
     @param db 数据库会话
     @param session_id 会话ID
     @return 生成笔记数据库模型实例列表
    """
    return db.query(db_models.GeneratedNote).filter(db_models.GeneratedNote.session_id == session_id).all()

def get_knowledge_cues_by_note_id(
    db: Session,
    note_id: str
) -> List[db_models.KnowledgeCue]:
    """
     获取与笔记关联的所有知识提示
     
     @param db 数据库会话
     @param note_id 笔记ID
     @return 知识提示数据库模型实例列表
    """
    return db.query(db_models.KnowledgeCue).filter(db_models.KnowledgeCue.note_id == note_id).all()

def update_learning_session_status(
    db: Session, 
    session_id: str, 
    status: ProcessingStatus
) -> Optional[db_models.LearningSession]:
    """
     更新学习会话状态
     
     @param db 数据库会话
     @param session_id 会话ID
     @param status 新的会话状态
     @return 更新后的学习会话数据库模型实例，如果不存在则返回None
    """
    db_session = get_learning_session(db, session_id)
    if db_session is None:
        return None
    
    # 更新状态
    db_session.status = status.value
    db.commit()
    db.refresh(db_session)
    return db_session

def update_learning_source_after_a1(
    db: Session, 
    video_id: str, 
    video_title_ai: str, 
    video_description_ai: str, 
    source_description_ai: str, 
    total_duration_seconds_ai: Optional[float], 
    structured_transcript_segments_json: str
) -> Optional[db_models.LearningSource]:
    """
     使用AI模块A.1处理结果更新学习资源
     
     @param db 数据库会话
     @param video_id 视频ID
     @param video_title_ai AI生成的视频标题
     @param video_description_ai AI生成的视频描述
     @param source_description_ai AI生成的资源描述
     @param total_duration_seconds_ai AI处理的视频总时长（秒）
     @param structured_transcript_segments_json AI结构化的转录片段JSON
     @return 更新后的学习资源数据库模型实例，如果不存在则返回None
    """
    # 获取学习资源
    db_source = db.query(db_models.LearningSource).filter(db_models.LearningSource.video_id == video_id).first()
    if db_source is None:
        return None
    
    # 更新字段
    db_source.video_title = video_title_ai
    db_source.video_description = video_description_ai
    db_source.source_description = source_description_ai
    db_source.total_duration_seconds = total_duration_seconds_ai
    db_source.structured_transcript_segments_json = structured_transcript_segments_json
    
    # 提交更改
    db.commit()
    db.refresh(db_source)
    return db_source

def update_learning_source_after_a2(
    db: Session, 
    video_id: str, 
    extracted_key_information_json: str
) -> Optional[db_models.LearningSource]:
    """
     使用AI模块A.2处理结果更新学习资源
     
     @param db 数据库会话
     @param video_id 视频ID
     @param extracted_key_information_json AI提取的关键信息JSON
     @return 更新后的学习资源数据库模型实例，如果不存在则返回None
    """
    # 获取学习资源
    db_source = db.query(db_models.LearningSource).filter(db_models.LearningSource.video_id == video_id).first()
    if db_source is None:
        return None
    
    # 更新提取的关键信息
    db_source.extracted_key_information_json = extracted_key_information_json
    
    # 提交更改
    db.commit()
    db.refresh(db_source)
    return db_source

def update_learning_source_objectives(
    db: Session,
    video_id: str,
    learning_objectives: Optional[str]
) -> Optional[db_models.LearningSource]:
    """
     Updates the learning_objectives field of a LearningSource record.

     @param db 数据库会话
     @param video_id 视频ID
     @param learning_objectives 用户提供的学习目标或重点
     @return 更新后的学习资源数据库模型实例，如果不存在则返回None
    """
    db_source = db.query(db_models.LearningSource).filter(db_models.LearningSource.video_id == video_id).first()
    if db_source is None:
        return None

    db_source.learning_objectives = learning_objectives
    db.commit()
    db.refresh(db_source)
    return db_source

def get_learning_source_by_video_id(db: Session, video_id: str) -> Optional[db_models.LearningSource]:
    """
    Retrieves a LearningSource record from the database by its video_id.

    Args:
        db: The SQLAlchemy database session.
        video_id: The video_id of the LearningSource to retrieve.

    Returns:
        The LearningSource object if found, otherwise None.
    """
    return db.query(db_models.LearningSource).filter(db_models.LearningSource.video_id == video_id).first()

def get_note_by_id(db: Session, note_id: str) -> Optional[db_models.GeneratedNote]:
    """
    Retrieves a GeneratedNote record from the database by its note_id.

    Args:
        db: The SQLAlchemy database session.
        note_id: The note_id of the GeneratedNote to retrieve.

    Returns:
        The GeneratedNote object if found, otherwise None.
    """
    return db.query(db_models.GeneratedNote).filter(db_models.GeneratedNote.note_id == note_id).first()

def update_note(
    db: Session, 
    note_id: str, 
    note_update_data: pydantic_models.NoteUpdate
) -> Optional[db_models.GeneratedNote]:
    """
    Updates a generated note in the database.

    Args:
        db: The SQLAlchemy database session.
        note_id: The ID of the note to update.
        note_update_data: A Pydantic model containing the data to update the note with.
                          Currently, this is expected to have `markdown_content`.

    Returns:
        The updated GeneratedNote object if found and updated, otherwise None.
    """
    db_note = get_note_by_id(db, note_id)
    if db_note is None:
        return None

    # Update the markdown content
    db_note.markdown_content = note_update_data.markdown_content
    # Set the flag indicating user edit
    db_note.is_user_edited = True
    # The last_edited_at field should be updated automatically by `onupdate=func.now()`
    # if the database and ORM model are configured correctly.
    # If `onupdate` is not reliably working or not desired for some reason,
    # you would explicitly set it here:
    # db_note.last_edited_at = datetime.now() 

    db.commit()
    db.refresh(db_note)
    return db_note