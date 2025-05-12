"""
 服务编排模块
 
 该模块负责协调各AI模块的工作流程，管理整个处理流程。
"""
import uuid
import json
import asyncio
import os
import shutil # Added for temporary directory cleanup
from datetime import datetime
from typing import Dict, Any, Optional, List
import tempfile

from sqlalchemy.orm import Session

from app.db import models as db_models
from app.db import crud
from app.db.database import SessionLocal
from app.core.config import Settings
from app.core.enums import ProcessingStatus # Added import
from app.utils.transcript_parser import parse_raw_transcript_to_segments
from app.utils.audio_processor import prepare_audio_for_asr
from app.services.asr.factory import get_asr_service
from app.services.asr.base import AbstractAsrService
from app.ai_modules.module_a1_llm_caller import invoke_module_a1_llm
from app.ai_modules.module_a2_llm_caller import invoke_module_a2_llm
from app.ai_modules.module_b_llm_caller import invoke_module_b_llm
from app.ai_modules.module_d_llm_caller import invoke_module_d_llm
from app.models.data_models import LearningSessionInput, GeneratedNoteRead, KnowledgeCueRead # Modified
# from app.ai_modules.module_d_knowledge_cues import generate_knowledge_cues # 已移除 # Keep this line if it was meant to be commented out.
from app.core.utils import normalize_bilibili_url

# Helper function to update status within its own session
def _update_status_in_session(session_id: str, status: ProcessingStatus):
    """Creates a local session to update the learning session status."""
    db_local: Session = SessionLocal()
    try:
        print(f"会话 {session_id}: [_update_status_in_session] 正在调用 crud.update_learning_session_status, 状态为 {status.value}")
        crud.update_learning_session_status(db_local, session_id, status)
        print(f"会话 {session_id}: [_update_status_in_session] 正在提交数据库事务...")
        db_local.commit()
        print(f"会话 {session_id}: [_update_status_in_session] 数据库事务提交成功。")
        print(f"会话 {session_id}: 状态更新为 {status.value}")
    except Exception as e:
        print(f"错误: 会话 {session_id}: [_update_status_in_session] 发生异常，正在回滚数据库事务...")
        db_local.rollback()
        print(f"错误: 会话 {session_id}: 更新状态 {status.value} 失败: {e}")
        raise
    finally:
        db_local.close()

# Helper function to get session object within its own session (used in error handling)
def _get_session_in_session(session_id: str) -> Optional[db_models.LearningSession]:
    """Creates a local session to get the learning session object."""
    db_local: Session = SessionLocal()
    try:
        print(f"会话 {session_id}: [_get_session_in_session] 正在调用 crud.get_learning_session")
        db_session = crud.get_learning_session(db_local, session_id)
        print(f"会话 {session_id}: [_get_session_in_session] crud.get_learning_session 调用完成。")
        return db_session
    except Exception as e:
        print(f"错误: 会话 {session_id}: [_get_session_in_session] 发生异常，正在回滚数据库事务 (如果适用)...")
        db_local.rollback() # Rollback read transaction just in case
        print(f"错误: 会话 {session_id}: 获取会话对象失败: {e}")
        return None # Return None on failure
    finally:
        db_local.close()

async def process_learning_session(raw_transcript: str, video_title: str = None, source_description: str = None) -> dict:
    """
     处理学习会话的完整流程
     
     @param raw_transcript 原始文本转录
     @param video_title 视频标题(可选)
     @param source_description 资源描述(可选)
     @return 处理结果，包含会话ID和状态
    """
    session_id = str(uuid.uuid4())
    return {
        "session_id": session_id,
        "status": "processing_initiated",
        "timestamp": datetime.now().isoformat()
    }

async def start_session_processing_pipeline(
    session_id: str, 
    video_id: str, 
    learning_session_input: LearningSessionInput,
    settings: Settings
) -> None:
    """
     启动会话处理管道
     
     如果提供了Bilibili URL，则执行视频下载（模拟）、音频提取和语音转文字，
     然后将转录文本送入AI模块。否则，直接处理提供的原始转录文本。
     协调AI模块的处理流程，按顺序执行模块A.1（转录预处理）、
     模块A.2（关键信息提取）、模块B（笔记生成）和模块D（知识提示生成）。
     
     @param session_id 会话ID
     @param video_id 视频ID (由API层创建/管理)
     @param learning_session_input 包含原始转录或B站URL及其他初始数据的输入对象
     @param settings 应用程序配置设置
    """
    module_a1_output: Dict[str, Any]
    module_a2_output: Dict[str, Any]
    
    parsed_segments_for_a1: List[Dict[str, Any]] = [] # Initialize for A1 input
    session_temp_base_dir: Optional[str] = None # For temporary file management and cleanup

    # Extract initial values from learning_session_input
    raw_transcript_text_from_input = learning_session_input.rawTranscriptText
    initial_video_title = learning_session_input.initialVideoTitle
    initial_source_description = learning_session_input.initialSourceDescription
    bilibili_url_pydantic_obj = learning_session_input.bilibili_video_url # Original Pydantic Url object

    processed_bilibili_url_str: Optional[str] = None # This will hold the normalized string URL

    # Normalize the Bilibili URL if it exists and store it as a string
    if bilibili_url_pydantic_obj:
        bilibili_url_as_string = str(bilibili_url_pydantic_obj) # Convert Pydantic Url to string
        processed_bilibili_url_str = normalize_bilibili_url(bilibili_url_as_string) # Pass string to normalizer
        # normalize_bilibili_url already returns a string or an empty string.

    # This will hold the transcript text to be processed by Module A1
    # transcript_for_a1: str = "" # No longer the primary way to pass transcript to A1 logic
    # session_temp_base_dir: Optional[str] = None # Defined earlier

    try:
        if processed_bilibili_url_str:
            print(f"会话 {session_id}: 检测到Bilibili URL: {processed_bilibili_url_str}。开始视频处理流程。")
            # Use helper for initial status update
            _update_status_in_session(session_id, ProcessingStatus.BILI_PROCESSING_STARTED)

            # a. Video Download
            print(f"会话 {session_id}: 创建临时目录用于视频处理...")
            session_temp_base_dir = tempfile.mkdtemp(prefix=f"session_{session_id}_")
            download_dir = os.path.join(session_temp_base_dir, "video_download")
            os.makedirs(download_dir, exist_ok=True)
            
            # Use a fixed name for the downloaded video for simplicity in this context
            downloaded_mp4_filename = "actual_bili_video.mp4"
            downloaded_mp4_path = os.path.join(download_dir, downloaded_mp4_filename)
            
            print(f"会话 {session_id}: 开始使用 yt-dlp 下载视频: {processed_bilibili_url_str} 到 {downloaded_mp4_path}")
            # Use helper for status update
            _update_status_in_session(session_id, ProcessingStatus.BILI_DOWNLOAD_ACTIVE)
            
            try:
                # Construct yt-dlp command
                # -o: output template
                # --no-warnings: suppress warnings
                # --quiet: suppress non-error output (optional, good for logs)
                # --progress: show progress (might be noisy in logs, consider removing if too verbose)
                # We want to ensure the video is downloaded as MP4. yt-dlp usually handles this well with -o *.mp4
                # or by default if format is available. Adding --merge-output-format mp4 for robustness.
                yt_dlp_command = [
                    'yt-dlp',
                    '--no-warnings', # Suppress common warnings
                    # '--quiet', # Suppress non-error console output if too noisy for logs
                    '--progress', # Show progress, can be verbose
                    '-o', downloaded_mp4_path,
                    '--merge-output-format', 'mp4', # Ensure MP4 output
                    processed_bilibili_url_str # Use the processed string URL
                ]
                print(f"会话 {session_id}: 执行 yt-dlp 命令: {' '.join(yt_dlp_command)}")
                
                import subprocess
                process_result = await asyncio.to_thread(
                    subprocess.run, yt_dlp_command, capture_output=True, text=True, check=False
                )

                if process_result.returncode != 0:
                    # yt-dlp often exits with 0 even on some download issues if it gets *something*,
                    # but a non-zero code is definitely an error.
                    # Log stderr for details.
                    print(f"错误: 会话 {session_id}: yt-dlp 下载失败。返回码: {process_result.returncode}")
                    print(f"yt-dlp stderr: {process_result.stderr}")
                    print(f"yt-dlp stdout: {process_result.stdout}") # Also log stdout for more context
                    # Use helper for status update
                    _update_status_in_session(session_id, ProcessingStatus.ERROR_BILI_DOWNLOAD_YT_DLP_FAILED)
                    raise Exception(f"yt-dlp download failed with exit code {process_result.returncode}. stderr: {process_result.stderr}")

                if not os.path.exists(downloaded_mp4_path) or os.path.getsize(downloaded_mp4_path) == 0:
                    print(f"错误: 会话 {session_id}: yt-dlp 命令成功执行，但未找到输出文件或文件为空: {downloaded_mp4_path}")
                    print(f"yt-dlp stdout (for context): {process_result.stdout}")
                    print(f"yt-dlp stderr (for context): {process_result.stderr}")
                    # Use helper for status update
                    _update_status_in_session(session_id, ProcessingStatus.ERROR_BILI_DOWNLOAD_FILE_MISSING)
                    raise Exception("yt-dlp executed but output file is missing or empty.")
                
                print(f"会话 {session_id}: yt-dlp 视频下载成功: {downloaded_mp4_path}")
                # Use helper for status update
                _update_status_in_session(session_id, ProcessingStatus.BILI_DOWNLOAD_SUCCESS)
            except Exception as download_exc:
                print(f"错误: 会话 {session_id}: 视频下载过程中发生错误: {download_exc}")
                # Check current status before setting a general error
                # Use helper to get session
                current_status_obj = _get_session_in_session(session_id)
                current_status_str = current_status_obj.status if current_status_obj else ""
                if not current_status_str.startswith("error_bili_download"):
                    # Use helper for status update
                    _update_status_in_session(session_id, ProcessingStatus.ERROR_BILI_DOWNLOAD)
                raise # Propagate to main error handler for pipeline

            # b. Audio Extraction
            print(f"会话 {session_id}: 开始音频提取...")
            # Use helper for status update
            _update_status_in_session(session_id, ProcessingStatus.BILI_AUDIO_EXTRACTION_ACTIVE)
            temp_audio_output_dir = os.path.join(session_temp_base_dir, "asr_audio")
            os.makedirs(temp_audio_output_dir, exist_ok=True)
            
            mp4_basename_no_ext = os.path.splitext(os.path.basename(downloaded_mp4_path))[0]

            compliant_wav_path = await asyncio.to_thread(
                prepare_audio_for_asr,
                video_name_no_ext=mp4_basename_no_ext,
                video_input_folder=os.path.dirname(downloaded_mp4_path),
                audio_output_folder=temp_audio_output_dir,
                output_filename_no_ext=f"{mp4_basename_no_ext}_compliant" 
            )

            if compliant_wav_path is None or not os.path.exists(compliant_wav_path):
                print(f"错误: 会话 {session_id}: 音频提取失败。prepare_audio_for_asr 未返回有效路径或文件不存在。")
                # Use helper for status update
                _update_status_in_session(session_id, ProcessingStatus.ERROR_AUDIO_EXTRACTION)
                raise Exception("Audio extraction failed.")
            print(f"会话 {session_id}: 音频提取成功，WAV文件: {compliant_wav_path}")
            # Use helper for status update
            _update_status_in_session(session_id, ProcessingStatus.BILI_AUDIO_EXTRACTION_SUCCESS)

            # c. Speech-to-Text (Xunfei)
            print(f"会话 {session_id}: 开始讯飞语音转文字...")
            # Use helper for status update
            _update_status_in_session(session_id, ProcessingStatus.BILI_ASR_ACTIVE)
            if not settings.XUNFEI_APPID or not settings.XUNFEI_SECRET_KEY:
                print(f"错误: 会话 {session_id}: 讯飞APPID或SECRET_KEY未在配置中设置。")
                # Use helper for status update
                _update_status_in_session(session_id, ProcessingStatus.ERROR_ASR_MISCONFIGURED)
                raise Exception("Xunfei ASR credentials not configured.")

            asr_client: AbstractAsrService = get_asr_service(settings)
            transcription_result_list = await asr_client.transcribe(audio_file_path=compliant_wav_path)

            if transcription_result_list is None: 
                print(f"错误: 会话 {session_id}: 讯飞语音转文字失败 (transcribe返回None)。")
                # Use helper for status update
                _update_status_in_session(session_id, ProcessingStatus.ERROR_ASR_FAILED)
                raise Exception("Xunfei ASR transcription failed (returned None).")

            # Attempt to convert ASR result list directly to structured segments
            _converted_segments = []
            if transcription_result_list: # Check if list is not None and potentially not empty
                for segment_data in transcription_result_list:
                    try:
                        start_ms = int(segment_data.get('bg', '0'))
                        end_ms = int(segment_data.get('ed', '0'))
                        text = segment_data.get('onebest', '').strip()
                        speaker = segment_data.get('speaker', "1") # Default speaker

                        if text: # Only add segments with actual text content
                            _converted_segments.append({
                                "speaker": speaker,
                                "start_time_ms": start_ms,
                                "end_time_ms": end_ms,
                                "text": text
                            })
                    except ValueError as ve:
                        print(f"警告: 会话 {session_id}: 转换ASR片段数据时出错 (ValueError for time conversion): {segment_data}, 错误: {ve}. 跳过此片段。")
                    except KeyError as ke:
                         print(f"警告: 会话 {session_id}: 转换ASR片段数据时缺少键: {segment_data}, 错误: {ke}. 跳过此片段。")
            
            if _converted_segments:
                parsed_segments_for_a1 = _converted_segments
                print(f"会话 {session_id}: 从ASR结果直接转换了 {len(parsed_segments_for_a1)} 个结构化片段。")
                # TODO: Refine transcript format adaptation for Module A.1 (ASR path) to include more detailed speaker/timing if available.
            else: # No structured segments from direct conversion (list was None, empty, or all segments had no text)
                # Fallback to using concatenated text if available
                full_transcript_text_fallback = ""
                if transcription_result_list: # transcription_result_list was not None, but _converted_segments is empty
                    full_transcript_text_fallback = " ".join([s.get('onebest', '') for s in transcription_result_list if s.get('onebest')]).strip()
                
                if full_transcript_text_fallback:
                    print(f"警告: 会话 {session_id}: 未能从ASR结果直接转换有效结构化片段。将使用连接后的完整转录文本 (长度 {len(full_transcript_text_fallback)}) 通过 parse_raw_transcript_to_segments 进行解析作为后备。")
                    parsed_segments_for_a1 = parse_raw_transcript_to_segments(full_transcript_text_fallback)
                else:
                    # This means transcription_result_list was None (handled by earlier error), or empty, or all 'onebest' were empty.
                    print(f"警告: 会话 {session_id}: ASR未能生成任何可用的转录文本（既无直接转换的结构化片段也无连接后的文本）。模块A.1将收到空输入。")
                    # parsed_segments_for_a1 remains []

            # Use helper for status update
            _update_status_in_session(session_id, ProcessingStatus.BILI_ASR_SUCCESS)
            
            # Logging the length of the (potentially used for fallback) concatenated transcript
            _log_full_transcript_text = ""
            if transcription_result_list:
                 _log_full_transcript_text = " ".join([segment.get('onebest', '') for segment in transcription_result_list if segment.get('onebest')]).strip()
            print(f"会话 {session_id}: 讯飞语音转文字处理完成。(连接后文本长度: {len(_log_full_transcript_text)} 字)")

            # transcript_for_a1 = full_transcript_text # This assignment is no longer the primary path for A1 input from Bili
            
        elif raw_transcript_text_from_input and raw_transcript_text_from_input.strip():
            print(f"会话 {session_id}: 检测到原始转录文本。开始直接处理。")
            # Use helper for status update
            _update_status_in_session(session_id, ProcessingStatus.TRANSCRIPT_PROCESSING_STARTED)
            parsed_segments_for_a1 = parse_raw_transcript_to_segments(raw_transcript_text_from_input)
            if not parsed_segments_for_a1:
                print(f"错误: 会话 {session_id}: 提供的原始转录文本解析后为空或无效。")
                # Consider a specific error status if needed, or let it fall to generic pipeline error
                # For now, let the generic error handler catch this if it propagates
                raise ValueError("Parsed raw transcript resulted in no segments.")
        else:
            print(f"错误: 会话 {session_id}: 未提供Bilibili URL或原始转录文本。")
            # Use helper for status update
            _update_status_in_session(session_id, ProcessingStatus.ERROR_NO_VALID_INPUT)
            raise ValueError("No valid input (Bilibili URL or raw transcript text) provided for the session.")

        # Common check for empty segments before A1 call
        if not parsed_segments_for_a1:
            print(f"警告: 会话 {session_id}: 为模块A.1准备的解析片段列表为空。后续处理可能产生空结果或失败。")
            # Module A1 should ideally handle an empty list gracefully.

        print(f"会话 {session_id}: 开始模块A.1 (转录预处理与元数据生成)...")
        # Use helper for status update
        _update_status_in_session(session_id, ProcessingStatus.A1_PREPROCESSING_ACTIVE)

        try:
            module_a1_output = await invoke_module_a1_llm(
                parsed_transcript_segments=parsed_segments_for_a1, 
                user_input_title=initial_video_title,
                user_input_source_desc=initial_source_description,
                settings=settings
            )
        except Exception as a1_exc:
            print(f"错误: 会话 {session_id}: 模块A.1 LLM调用失败: {a1_exc}")
            # Use helper for status update
            _update_status_in_session(session_id, ProcessingStatus.ERROR_IN_A1_LLM)
            raise 

        # --- Database operations after Module A.1 ---
        db_local: Session = SessionLocal()
        try:
            current_iso_timestamp = datetime.now().isoformat()
            if module_a1_output.get("processingTimestamp") == "[SYSTEM_GENERATED_TIMESTAMP_YYYY-MM-DDTHH:MM:SSZ]":
                module_a1_output["processingTimestamp"] = current_iso_timestamp
            else:
                print(f"警告: 会话 {session_id}: 模块A.1 LLM未按预期提供时间戳占位符。 使用当前时间。 LLM时间戳: {module_a1_output.get('processingTimestamp')}")
                module_a1_output["processingTimestamp"] = current_iso_timestamp

            if "videoId" in module_a1_output and module_a1_output["videoId"] != video_id:
                print(f"警告: 会话 {session_id}: 模块A.1 LLM生成的videoId '{module_a1_output['videoId']}' 与系统中已有的videoId '{video_id}' 不符。将使用系统videoId.")

            crud.update_learning_source_after_a1(
                db=db_local, # Use local session
                video_id=video_id, 
                video_title_ai=module_a1_output["videoTitle"],
                video_description_ai=module_a1_output["videoDescription"],
                source_description_ai=module_a1_output["sourceDescription"],
                total_duration_seconds_ai=module_a1_output.get("totalDurationSeconds"),
                structured_transcript_segments_json=json.dumps(
                    module_a1_output["transcriptSegments"],
                    ensure_ascii=False
                )
            )
            db_local.commit()
            # Status update handled separately by helper
            print(f"会话 {session_id}: 模块A.1处理完成，信息已保存。")
        except Exception as e_db_a1:
            print(f"错误: 会话 {session_id}: 保存模块A.1结果失败: {e_db_a1}")
            db_local.rollback()
            raise
        finally:
            db_local.close()

        # Update status after A.1 DB operations are complete (even if A1 LLM failed, DB save could succeed if A1 output was mocked/partial)
        # But the try...except above re-raises, so this status update only happens if DB save was attempted AND succeeded.
        # To ensure status update happens even if DB save fails BUT LLM succeeded, need careful placement.
        # Let's move status update outside the inner DB try/except but still after LLM call.
        _update_status_in_session(session_id, ProcessingStatus.A1_PREPROCESSING_COMPLETE) # This will create its own session

        print(f"会话 {session_id}: 开始模块A.2 (关键信息提取)...")
        # Use helper for status update
        _update_status_in_session(session_id, ProcessingStatus.A2_EXTRACTION_ACTIVE)
        
        try:
            module_a2_output = await invoke_module_a2_llm(
                module_a1_llm_output=module_a1_output, 
                settings=settings
            )
        except Exception as a2_exc:
            print(f"错误: 会话 {session_id}: 模块A.2 LLM调用失败: {a2_exc}")
            # Use helper for status update
            _update_status_in_session(session_id, ProcessingStatus.ERROR_IN_A2_LLM)
            raise

        # --- Database operations after Module A.2 ---
        db_local: Session = SessionLocal()
        try:
            a2_processing_timestamp = module_a2_output.get("processingTimestamp")
            if a2_processing_timestamp == "[SYSTEM_GENERATED_TIMESTAMP_YYYY-MM-DDTHH:MM:SSZ]" or not a2_processing_timestamp:
                print(f"会话 {session_id}: 模块A.2 LLM未提供有效时间戳或使用了占位符。使用当前时间。 LLM时间戳: {a2_processing_timestamp}")
                module_a2_output["processingTimestamp"] = datetime.now().isoformat()

            crud.update_learning_source_after_a2(
                db=db_local, # Use local session
                video_id=video_id, 
                extracted_key_information_json=json.dumps(
                    module_a2_output["extractedKeyInformation"],
                    ensure_ascii=False
                )
            )
            db_local.commit()
            # Status update handled separately by helper
            print(f"会话 {session_id}: 模块A.2处理完成，信息已保存。")
        except Exception as e_db_a2:
            print(f"错误: 会话 {session_id}: 保存模块A.2结果失败: {e_db_a2}")
            db_local.rollback()
            raise
        finally:
            db_local.close()

        # Update status after A.2 DB operations are complete
        _update_status_in_session(session_id, ProcessingStatus.A2_EXTRACTION_COMPLETE)
        print(f"会话 {session_id}: 模块A.2处理完成。")
        
        print(f"会话 {session_id}: 开始模块B (笔记生成)...")
        # Use helper for status update
        _update_status_in_session(session_id, ProcessingStatus.NOTE_GENERATION_ACTIVE)
        
        real_module_b_output: Dict[str, Any]
        try:
            real_module_b_output = await invoke_module_b_llm(
                module_a1_output=module_a1_output,
                module_a2_output=module_a2_output,
                settings=settings
            )
        except Exception as b_exc:
            print(f"错误: 会话 {session_id}: 模块B LLM调用失败: {b_exc}")
            # Use helper for status update
            _update_status_in_session(session_id, ProcessingStatus.ERROR_IN_B_LLM)
            raise

        b_processing_timestamp = real_module_b_output.get("generationTimestamp")
        if b_processing_timestamp == "[SYSTEM_GENERATED_TIMESTAMP_YYYY-MM-DDTHH:MM:SSZ]" or not b_processing_timestamp:
            print(f"会话 {session_id}: 模块B LLM未提供有效时间戳或使用了占位符。使用当前时间。 LLM时间戳: {b_processing_timestamp}")
            real_module_b_output["generationTimestamp"] = datetime.now().isoformat()

        db_note = crud.create_generated_note(
            db=db_local,
            video_id=video_id, 
            session_id=session_id,
            note_markdown_content=real_module_b_output["noteMarkdownContent"],
            estimated_reading_time_seconds=real_module_b_output.get("estimatedReadingTimeSeconds"),
            key_concepts_mentioned=real_module_b_output.get("keyConceptsMentioned"),
            summary_of_note=real_module_b_output.get("summaryOfNote"),
            user_id=None 
        )
        # Use helper for status update
        _update_status_in_session(session_id, ProcessingStatus.NOTE_GENERATION_COMPLETE)
        print(f"会话 {session_id}: 模块B处理完成。笔记ID: {db_note.note_id}")
        
        print(f"会话 {session_id}: 开始模块D (知识提示生成)...")
        # Use helper for status update
        _update_status_in_session(session_id, ProcessingStatus.KNOWLEDGE_CUES_GENERATION_ACTIVE)
        
        real_d_output: Dict[str, Any]
        try:
            real_d_output = await invoke_module_d_llm(
                note_markdown_content=db_note.markdown_content,
                key_concepts_list=db_note.key_concepts_mentioned, 
                note_summary=db_note.summary_of_note,
                video_id=video_id, 
                note_id=db_note.note_id, 
                settings=settings
            )
        except Exception as d_exc:
            print(f"错误: 会话 {session_id}: 模块D LLM调用失败: {d_exc}")
            # Use helper for status update
            _update_status_in_session(session_id, ProcessingStatus.ERROR_IN_D_LLM)
            raise

        d_processing_timestamp = real_d_output.get("generationTimestamp")
        if d_processing_timestamp == "[SYSTEM_GENERATED_TIMESTAMP_YYYY-MM-DDTHH:MM:SSZ]" or not d_processing_timestamp:
            print(f"会话 {session_id}: 模块D LLM未提供有效时间戳或使用了占位符。使用当前时间。 LLM时间戳: {d_processing_timestamp}")
            
        knowledge_cues_from_d = real_d_output.get("knowledgeCues", [])
        if not isinstance(knowledge_cues_from_d, list):
            print(f"警告: 会话 {session_id}: 模块D LLM 返回的 'knowledgeCues' 不是列表，而是一个 {type(knowledge_cues_from_d)}。将使用空列表。")
            knowledge_cues_from_d = []

        for cue_data in knowledge_cues_from_d:
            if not all(k in cue_data for k in ["questionText", "answerText", "difficultyLevel"]):
                print(f"警告: 会话 {session_id}: 模块D LLM 返回的 cue_data 缺少必要字段: {cue_data}。跳过此提示。")
                continue
                
            crud.create_knowledge_cue(
                db=db_local, # Use the local session
                note_id=db_note.note_id, # Use note_id from the ORM object
                question_text=cue_data["questionText"],
                answer_text=cue_data["answerText"],
                difficulty_level=cue_data["difficultyLevel"],
                source_reference_in_note=cue_data.get("sourceReferenceInNote")
            )
            print(f"会话 {session_id}: 已从模块D生成知识提示: {cue_data['questionText'][:50]}...")
        
        # Use helper for status update
        _update_status_in_session(session_id, ProcessingStatus.KNOWLEDGE_CUES_GENERATION_COMPLETE)
        print(f"会话 {session_id}: 模块D处理完成。")
        
        # Final Status Update (Success)
        # Use helper for final status update
        _update_status_in_session(session_id, ProcessingStatus.ALL_PROCESSING_COMPLETE)
        print(f"会话 {session_id}: 所有处理步骤成功完成。")

    except Exception as e:
        print(f"错误: 会话 {session_id}: 处理管道中发生未捕获的异常: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

        # Error Status Update
        # Need a new session here as the previous one might be invalid due to the caught exception
        # Use helper to get session
        current_session_status_obj = _get_session_in_session(session_id)
        # Only update status if it's not already an error status
        if current_session_status_obj and not current_session_status_obj.status.startswith("error_"):
             # Use helper to update status
             _update_status_in_session(session_id, ProcessingStatus.ERROR_PIPELINE_FAILED)
        else:
             print(f"会话 {session_id}: 管道失败，但状态已是错误状态 ({current_session_status_obj.status if current_session_status_obj else 'N/A'})，不再更新。")

    finally:
        # This outer finally only handles cleanup like temporary files
        if session_temp_base_dir and os.path.exists(session_temp_base_dir):
            try:
                await asyncio.to_thread(shutil.rmtree, session_temp_base_dir)
                print(f"会话 {session_id}: 临时目录 {session_temp_base_dir} 已成功清理。")
            except Exception as e_cleanup:
                print(f"错误: 会话 {session_id}: 清理临时目录 {session_temp_base_dir} 失败: {e_cleanup}")

def _simulate_module_a1_output(raw_text_placeholder: str, input_video_id: str) -> Dict[str, Any]:
    """
     模拟模块A.1的输出
     @return 模拟的模块A.1输出
    """
    is_chinese = any('\u4e00' <= char <= '\u9fff' for char in raw_text_placeholder)
    video_title = "模拟AI生成标题 (A1) - [中文]" if is_chinese else "Simulated AI Title (A1) - [English]"
    video_description = "模拟AI生成的视频描述 (A1) - [中文]" if is_chinese else "Simulated AI Description for video (A1) - [English]"
    source_description = "模拟源描述 (A1) - [中文]" if is_chinese else "Simulated Source Description (A1) - [English]"
    segment_text_1 = "这是来自A1的模拟转录片段1 - [中文]" if is_chinese else "This is a simulated transcript segment 1 from A1 - [English]"
    segment_text_2 = "这是来自A1的模拟转录片段2 - [中文]" if is_chinese else "This is a simulated transcript segment 2 from A1 - [English]"
    timestamp = "[SYSTEM_GENERATED_TIMESTAMP_YYYY-MM-DDTHH:MM:SSZ]"
    return {
        "videoId": input_video_id,
        "videoTitle": video_title,
        "videoDescription": video_description,
        "sourceDescription": source_description,
        "processingTimestamp": timestamp,
        "totalDurationSeconds": 120.0,
        "transcriptSegments": [
            {"segmentId": "sim_seg_001", "startTimeSeconds": 0.0, "endTimeSeconds": 60.0, "text": segment_text_1},
            {"segmentId": "sim_seg_002", "startTimeSeconds": 60.1, "endTimeSeconds": 120.0, "text": segment_text_2}
        ]
    }

def _simulate_module_a2_output(module_a1_output_data: Dict[str, Any]) -> Dict[str, Any]:
    """
     模拟模块A.2的输出
     @return 模拟的模块A.2输出
    """
    video_id = module_a1_output_data.get("videoId", "unknown_video_id")
    video_title = module_a1_output_data.get("videoTitle", "")
    is_chinese = any('\u4e00' <= char <= '\u9fff' for char in video_title)
    transcript_segments = module_a1_output_data.get("transcriptSegments", [])
    segment_ids = [seg.get("segmentId") for seg in transcript_segments if "segmentId" in seg] or ["sim_seg_001"]
    start_time_1, end_time_1 = (transcript_segments[0]["startTimeSeconds"], transcript_segments[0]["endTimeSeconds"]) if transcript_segments else (0.0, 30.0)
    start_time_2, end_time_2 = (transcript_segments[1]["startTimeSeconds"], transcript_segments[1]["endTimeSeconds"]) if len(transcript_segments) > 1 else (60.0, 90.0)
    
    if is_chinese:
        key_concept = "模拟的关键概念定义 (A2) - [中文]"
        main_topic = "模拟的主要主题标题 (A2) - [中文]"
        summary_1, summary_2 = "这是模拟的概念摘要 - [中文]", "这是模拟的主题摘要 - [中文]"
        keywords_1, keywords_2 = ["关键词1", "关键词2", "关键词3"], ["主题词1", "主题词2"]
        note_1, note_2 = "关于该概念的上下文注释 - [中文]", "关于该主题的上下文注释 - [中文]"
    else:
        key_concept = "Simulated key concept definition (A2) - [English]"
        main_topic = "Simulated main topic title (A2) - [English]"
        summary_1, summary_2 = "This is a simulated concept summary - [English]", "This is a simulated topic summary - [English]"
        keywords_1, keywords_2 = ["keyword1", "keyword2", "keyword3"], ["topic1", "topic2"]
        note_1, note_2 = "Contextual note about this concept - [English]", "Contextual note about this topic - [English]"
        
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "videoId": video_id,
        "processingTimestamp": timestamp,
        "extractedKeyInformation": [
            {"itemId": "sim_ki_001", "itemType": "key_concept_definition", "extractedText": key_concept, "sourceSegmentIds": [segment_ids[0]], "startTimeSeconds": start_time_1, "endTimeSeconds": end_time_1, "summary": summary_1, "keywords": keywords_1, "contextualNote": note_1},
            {"itemId": "sim_ki_002", "itemType": "main_topic_or_section_title", "extractedText": main_topic, "sourceSegmentIds": segment_ids, "startTimeSeconds": start_time_2, "endTimeSeconds": end_time_2, "summary": summary_2, "keywords": keywords_2, "contextualNote": note_2}
        ]
    }

def _simulate_module_b_output(module_a1_output_data: Dict[str, Any], module_a2_output_data: Dict[str, Any]) -> Dict[str, Any]:
    """
     模拟模块B的输出
     @return 模拟的模块B输出
    """
    video_id = module_a1_output_data.get("videoId", "unknown_video_id")
    video_title = module_a1_output_data.get("videoTitle", "")
    is_chinese = any('\u4e00' <= char <= '\u9fff' for char in video_title)
    note_id = f"sim_note_{uuid.uuid4().hex[:8]}"
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    key_concepts = []
    extracted_info = module_a2_output_data.get("extractedKeyInformation", [])
    for item in extracted_info:
        if item.get("keywords") and isinstance(item["keywords"], list):
            key_concepts.extend(item["keywords"])
    
    if not key_concepts:
        key_concepts = ["模拟概念1_来自B", "模拟概念2_来自B"] if is_chinese else ["SimulatedConcept1_from_B", "SimulatedConcept2_from_B"]
    
    key_concepts = key_concepts[:5]

    if is_chinese:
        note_title_md = f"# {video_title} - 学习笔记"
        note_intro_md = "\n\n这是由模块B生成的模拟Markdown笔记内容。这个笔记基于视频内容和提取的关键信息生成。\n\n"
        note_section1_md = "## 第一部分：主要概念\n\n这部分讨论了视频中的主要概念。(视频 00:15)\n\n"
        note_section2_md = "## 第二部分：重要观点\n\n这部分讨论了视频中的重要观点。(视频 01:30)\n\n"
        note_conclusion_md = "## 总结\n\n这个视频涵盖了几个重要概念，包括上面讨论的内容。"
        note_content_md = note_title_md + note_intro_md + note_section1_md + note_section2_md + note_conclusion_md
        summary_text = "这是模块B生成的笔记摘要，总结了视频的主要内容和关键点。- [中文]"
    else:
        note_title_md = f"# {video_title} - Study Notes"
        note_intro_md = "\n\nThis is a simulated Markdown note content generated by Module B. This note is based on the video content and extracted key information.\n\n"
        note_section1_md = "## Part 1: Main Concepts\n\nThis section discusses the main concepts from the video. (Video 00:15)\n\n"
        note_section2_md = "## Part 2: Important Points\n\nThis section discusses the important points from the video. (Video 01:30)\n\n"
        note_conclusion_md = "## Conclusion\n\nThis video covered several important concepts including those discussed above."
        note_content_md = note_title_md + note_intro_md + note_section1_md + note_section2_md + note_conclusion_md
        summary_text = "This is a summary of the note generated by Module B, summarizing the main content and key points from the video. - [English]"
    
    return {
        "videoId": video_id,
        "noteId": note_id,
        "generationTimestamp": timestamp,
        "noteMarkdownContent": note_content_md,
        "estimatedReadingTimeSeconds": 180,
        "keyConceptsMentioned": key_concepts,
        "summaryOfNote": summary_text
    }

def _simulate_module_d_output(
    note_markdown_content: str, 
    key_concepts_list: Optional[List[str]], 
    note_summary: Optional[str], 
    video_id: str, 
    note_id: str
) -> Dict[str, Any]:
    """
     模拟模块D的输出：生成知识提示
     
     @param note_markdown_content 笔记Markdown内容
     @param key_concepts_list 关键概念列表 (应为List[str]或None)
     @param note_summary 笔记摘要
     @param video_id 视频ID
     @param note_id 笔记ID
     @return 模拟的模块D输出，包含知识提示
    """
    is_chinese = any('\u4e00' <= char <= '\u9fff' for char in note_markdown_content)
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    knowledge_cues = []
    
    difficulties = ["low"] * 2 + ["high"] * 3
    
    for i, diff in enumerate(difficulties):
        if is_chinese:
            q_text = f"模拟问题 {i+1} ({diff}) - [中文]"
            a_text = f"模拟答案 {i+1} ({diff}) - 这是与问题相关的详细答案内容。 - [中文]"
            src_ref = f"笔记参考 {i+1} - [中文]"
        else:
            q_text = f"Simulated Question {i+1} ({diff}) - [English]"
            a_text = f"Simulated Answer {i+1} ({diff}) - This is a detailed answer text related to the question. - [English]"
            src_ref = f"Note Reference {i+1} - [English]"
        
        knowledge_cues.append({
            "questionText": q_text,
            "answerText": a_text,
            "difficultyLevel": diff,
            "sourceReferenceInNote": src_ref
        })
        
    return {
        "videoId": video_id,
        "noteId": note_id,
        "generationTimestamp": timestamp,
        "knowledgeCues": knowledge_cues
    }
