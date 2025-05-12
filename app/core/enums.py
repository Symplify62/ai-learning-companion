from enum import Enum

class ProcessingStatus(str, Enum):
    """Defines the comprehensive set of processing statuses for a learning session."""
    PROCESSING_INITIATED = "processing_initiated"
    TRANSCRIPT_PROCESSING_STARTED = "transcript_processing_started" # For raw text input path
    BILI_PROCESSING_STARTED = "bili_processing_started"
    BILI_DOWNLOAD_ACTIVE = "bili_download_active"
    BILI_DOWNLOAD_SUCCESS = "bili_download_success"
    ERROR_BILI_DOWNLOAD_YT_DLP_FAILED = "error_bili_download_yt_dlp_failed"
    ERROR_BILI_DOWNLOAD_FILE_MISSING = "error_bili_download_file_missing"
    ERROR_BILI_DOWNLOAD = "error_bili_download" # Generic download error
    BILI_AUDIO_EXTRACTION_ACTIVE = "bili_audio_extraction_active"
    BILI_AUDIO_EXTRACTION_SUCCESS = "bili_audio_extraction_success"
    ERROR_AUDIO_EXTRACTION = "error_audio_extraction"
    BILI_ASR_ACTIVE = "bili_asr_active"
    BILI_ASR_SUCCESS = "bili_asr_success"
    ERROR_ASR_MISCONFIGURED = "error_asr_misconfigured"
    ERROR_ASR_FAILED = "error_asr_failed"
    A1_PREPROCESSING_ACTIVE = "a1_preprocessing_active"
    A1_PREPROCESSING_COMPLETE = "a1_preprocessing_complete"
    ERROR_IN_A1_LLM = "error_in_a1_llm"
    A2_EXTRACTION_ACTIVE = "a2_extraction_active"
    A2_EXTRACTION_COMPLETE = "a2_extraction_complete"
    ERROR_IN_A2_LLM = "error_in_a2_llm"
    NOTE_GENERATION_ACTIVE = "note_generation_active"
    NOTE_GENERATION_COMPLETE = "note_generation_complete"
    ERROR_IN_B_LLM = "error_in_b_llm"
    KNOWLEDGE_CUES_GENERATION_ACTIVE = "knowledge_cues_generation_active"
    KNOWLEDGE_CUES_GENERATION_COMPLETE = "knowledge_cues_generation_complete"
    ERROR_IN_D_LLM = "error_in_d_llm"
    ALL_PROCESSING_COMPLETE = "all_processing_complete"
    ERROR_NO_VALID_INPUT = "error_no_valid_input"
    ERROR_PIPELINE_FAILED = "error_pipeline_failed" # Generic pipeline failure 