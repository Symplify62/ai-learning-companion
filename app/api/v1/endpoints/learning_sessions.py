import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Body, Depends, HTTPException, Path, BackgroundTasks
from sqlalchemy.orm import Session
import json

from app.core.enums import ProcessingStatus
from app.models.data_models import (
    LearningSessionInput, 
    LearningSessionResponse,
    LearningSessionDetail,
    NoteWithCues,
    FinalResultsPayload,
    GeneratedNoteRead,
    KnowledgeCueRead,
    NoteUpdate # Added for note updates
)
from app.db.database import get_db
from app.db import crud
from app.db.models import LearningSession as DbLearningSession
from app.services.orchestration import start_session_processing_pipeline
from app.core.config import Settings, get_settings

router = APIRouter()

@router.post("/", response_model=LearningSessionResponse)
async def create_learning_session(
    session_input: LearningSessionInput = Body(...),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None,
    settings: Settings = Depends(get_settings)
) -> LearningSessionResponse:
    """
     创建新的学习会话
     
     @param session_input 学习会话输入数据
     @param db 数据库会话（通过依赖注入）
     @param background_tasks 后台任务队列（用于异步处理）
     @param settings 配置设置
     @return LearningSessionResponse 新创建的学习会话信息
    """
    # The LearningSessionInput model's root_validator now handles these checks.
    # try:
    #     # Example: Access validated source_type (it's guaranteed to be set by the validator)
    #     print(f"Validated source_type: {session_input.source_type}")
    # except ValueError as e: # Should be caught by FastAPI if Pydantic validation fails
    #     raise HTTPException(status_code=422, detail=str(e))

    try:
        # 步骤1: 在数据库中创建新的学习会话记录
        db_session = crud.create_learning_session(
            db=db,
            status=ProcessingStatus.PROCESSING_INITIATED,
            user_id=None  # 目前没有用户认证，将来可以添加
        )
        
        # 步骤2: 使用session_id创建学习资源记录
        db_source = crud.create_learning_source(
            db=db,
            session_id=db_session.session_id,
            video_title=session_input.initialVideoTitle if session_input.initialVideoTitle else "Untitled Video - Pending AI Processing",
            initial_source_description=session_input.initialSourceDescription,
            user_id=None  # 目前没有用户认证，将来可以添加
        )
        
        # 步骤3: 添加后台任务，启动处理管道
        if background_tasks:
            background_tasks.add_task(
                start_session_processing_pipeline,
                session_id=db_session.session_id,
                settings=settings,
                video_id=db_source.video_id,
                learning_session_input=session_input, # This now contains the validated source_type
                learning_objectives=session_input.learning_objectives
            )
        
        # 返回响应
        return LearningSessionResponse(
            sessionId=db_session.session_id,
            status=db_session.status
        )
    except Exception as e:
        # 发生异常时回滚事务
        db.rollback()
        # 记录错误并引发HTTP异常
        raise HTTPException(
            status_code=500, 
            detail=f"创建学习会话失败: {str(e)}"
        )

@router.get("/{session_id}/status", response_model=LearningSessionDetail)
async def get_learning_session_status(
    session_id: str,
    db: Session = Depends(get_db)
) -> LearningSessionDetail:
    db_session = crud.get_learning_session(db, session_id)
    if db_session is None:
        raise HTTPException(status_code=404, detail=f"Session ID {session_id} not found")

    final_results_payload: Optional[FinalResultsPayload] = None

    if db_session.status == "all_processing_complete":
        notes_with_cues_list = []
        db_notes = crud.get_notes_by_session_id(db, session_id=session_id)
        
        if db_notes:
            for db_note in db_notes:
                db_cues = crud.get_knowledge_cues_by_note_id(db, note_id=db_note.note_id)
                
                cues_read_list = [KnowledgeCueRead.model_validate(cue) for cue in db_cues] if db_cues else []
                
                note_data_for_payload = GeneratedNoteRead.model_validate(db_note)
                note_with_cues_item = NoteWithCues(
                    **note_data_for_payload.model_dump(),
                    knowledge_cues=cues_read_list
                )
                notes_with_cues_list.append(note_with_cues_item)
        
        final_results_payload = FinalResultsPayload(notes=notes_with_cues_list)

        # --- Added logic to populate transcript fields ---
        if final_results_payload.notes: # Ensure there's at least one note to get video_id
            video_id_for_source = final_results_payload.notes[0].video_id
            db_learning_source = crud.get_learning_source_by_video_id(db=db, video_id=video_id_for_source)

            if db_learning_source and db_learning_source.structured_transcript_segments_json:
                try:
                    timestamped_segments = json.loads(db_learning_source.structured_transcript_segments_json)
                    final_results_payload.timestamped_transcript_segments = timestamped_segments
                    
                    plain_text_parts = []
                    if isinstance(timestamped_segments, list):
                        for segment in timestamped_segments:
                            if isinstance(segment, dict) and segment.get('text'):
                                plain_text_parts.append(str(segment['text']))
                    
                    final_results_payload.plain_transcript_text = "\n".join(plain_text_parts).strip()
                except json.JSONDecodeError:
                    # Handle error if JSON is malformed, or log it
                    # For now, fields will remain None if parsing fails
                    pass # Or log: print(f"Error decoding transcript JSON for source {video_id_for_source}")

                # Add AI generated title
                final_results_payload.ai_generated_video_title = db_learning_source.video_title
                if not final_results_payload.ai_generated_video_title:
                    print(f"Warning: LearningSource (ID: {video_id_for_source}) has empty video_title")
        # --- End of added logic ---

    session_detail = LearningSessionDetail.model_validate(db_session)
    session_detail.final_results = final_results_payload

    # Ensure the status is correctly cast to the enum if not already
    # This should be handled by Pydantic model validation, but as a safeguard:
    if isinstance(session_detail.status, str):
        try:
            session_detail.status = ProcessingStatus(session_detail.status)
        except ValueError:
            # Log an error or handle if the status string is not a valid enum member
            # This case should ideally not happen if DB stores valid enum values.
            print(f"Warning: Invalid status value '{session_detail.status}' found for session {session_id}")
            # Fallback or raise error, depending on desired behavior.
            # For now, let Pydantic's validation handle it or keep as string if it fails before this.
            pass

    return session_detail

@router.patch("/{session_id}/status", response_model=LearningSessionResponse)
async def update_learning_session_status_manual(
    session_id: str = Path(..., description="The ID of the session to update"),
    status_update: LearningSessionResponse = Body(..., description="The new status for the session"),
    db: Session = Depends(get_db)
) -> LearningSessionResponse:
    """
     更新学习会话状态
     
     @param session_id 会话ID
     @param status_update 新的会话状态
     @param db 数据库会话（通过依赖注入）
     @return LearningSessionResponse 更新后的会话信息
    """
    try:
        # 更新会话状态
        updated_session = crud.update_learning_session_status(db, session_id, status_update.status)
        
        # 如果会话不存在，返回404错误
        if updated_session is None:
            raise HTTPException(status_code=404, detail=f"Session ID {session_id} not found")
        
        # 返回更新后的会话信息
        return LearningSessionResponse(
            sessionId=updated_session.session_id,
            status=updated_session.status
        )
    except Exception as e:
        # 发生异常时回滚事务
        db.rollback()
        # 记录错误并引发HTTP异常
        raise HTTPException(
            status_code=500, 
            detail=f"更新会话状态失败: {str(e)}"
        )

@router.get("/{session_id}/source", response_model=Dict[str, Any])
async def get_session_source(
    session_id: str = Path(..., description="会话ID"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
     获取与会话关联的学习资源
     
     @param session_id 会话ID
     @param db 数据库会话（通过依赖注入）
     @return 学习资源信息
    """
    # 获取会话关联的学习资源
    db_source = crud.get_learning_source_by_session_id(db, session_id)
    
    # 如果资源不存在，返回404错误
    if db_source is None:
        raise HTTPException(status_code=404, detail=f"会话ID {session_id} 没有关联的学习资源")
    
    # 构建响应
    return {
        "video_id": db_source.video_id,
        "session_id": db_source.session_id,
        "video_title": db_source.video_title,
        "video_description": db_source.video_description,
        "source_description": db_source.source_description,
        "total_duration_seconds": db_source.total_duration_seconds,
        "has_structured_transcript": db_source.structured_transcript_segments_json is not None,
        "has_extracted_key_information": db_source.extracted_key_information_json is not None
    }

@router.get("/{session_id}/notes", response_model=List[Dict[str, Any]])
async def get_session_notes(
    session_id: str = Path(..., description="会话ID"),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
     获取与会话关联的生成笔记
     
     @param session_id 会话ID
     @param db 数据库会话（通过依赖注入）
     @return 生成笔记列表
    """
    # 获取会话关联的生成笔记列表
    notes = crud.get_notes_by_session_id(db, session_id)
    
    # 如果没有找到笔记，返回空列表
    if not notes:
        return []
    
    # 转换数据库模型为响应格式
    result = []
    for note in notes:
        # key_concepts_mentioned 现在应该直接是来自JSON列的列表
        key_concepts = []
        if isinstance(note.key_concepts_mentioned, list):
            key_concepts = note.key_concepts_mentioned
        elif note.key_concepts_mentioned is not None: # 如果不是列表但存在，尝试作为字符串处理或记录
            # 为了简单起见，如果不是预期的列表，我们将其作为单个元素的字符串列表
            # 在实际应用中，这里可能需要更复杂的错误处理或数据迁移逻辑
            print(f"Warning: key_concepts_mentioned for note {note.note_id} is not a list, but: {type(note.key_concepts_mentioned)}")
            key_concepts = [str(note.key_concepts_mentioned)]

        # 构建笔记响应对象
        note_data = {
            "note_id": note.note_id,
            "video_id": note.video_id,
            "session_id": note.session_id,
            "markdown_content": note.markdown_content,
            "is_user_edited": note.is_user_edited,
            "version": note.version,
            "created_at": note.created_at, # 已经是ISO格式字符串
            "last_modified_at": note.last_modified_at, # 已经是ISO格式字符串
            "estimated_reading_time_seconds": note.estimated_reading_time_seconds,
            "key_concepts_mentioned": key_concepts,
            "summary_of_note": note.summary_of_note
        }
        result.append(note_data)
    
    return result

@router.get("/notes/{note_id}/knowledge_cues", response_model=List[Dict[str, Any]])
async def get_note_knowledge_cues(
    note_id: str = Path(..., description="笔记ID"),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
     获取与笔记关联的知识提示
     
     @param note_id 笔记ID
     @param db 数据库会话（通过依赖注入）
     @return 知识提示列表
    """
    # 获取与笔记关联的知识提示列表
    knowledge_cues = crud.get_knowledge_cues_by_note_id(db, note_id)
    
    # 如果没有找到知识提示，返回空列表
    if not knowledge_cues:
        return []
    
    # 转换数据库模型为响应格式
    result = []
    for cue in knowledge_cues:
        # 构建知识提示响应对象
        cue_data = {
            "cue_id": cue.cue_id,
            "note_id": cue.note_id,
            "question_text": cue.question_text,
            "answer_text": cue.answer_text,
            "difficulty_level": cue.difficulty_level,
            "source_reference_in_note": cue.source_reference_in_note,
            "created_at": cue.created_at,
            "last_modified_at": cue.last_modified_at
        }
        result.append(cue_data)
    
    return result
