import asyncio
import os
import uuid
import logging
from pathlib import Path

# Set environment variables for Xunfei and a test DB *before* importing app modules
# This allows app.core.config.get_settings() to pick them up.
os.environ["XUNFEI_APPID"] = "0d717445"
os.environ["XUNFEI_SECRET_KEY"] = "a118aa53fce30066451688ae0adf6a3a"
# For local testing, use a SQLite DB. Ensure aiosqlite is installed in the venv.
# The path will be relative to where this script is run (project root).
DATABASE_FILE_PATH = "test_orchestration_runner.db"
if os.path.exists(DATABASE_FILE_PATH):
    os.remove(DATABASE_FILE_PATH) # Clean up from previous runs
os.environ["DATABASE_URL_FOR_RUNNER"] = f"sqlite+aiosqlite:///./{DATABASE_FILE_PATH}"
# We also need to ensure app.core.config.Settings expects this env var,
# or that app.db.database.SQLALCHEMY_DATABASE_URL uses it.
# For now, let's assume base Settings in app.core.config.py can pick up a general
# DATABASE_URL, or we modify it to look for DATABASE_URL_FOR_RUNNER if present.
# For simplicity of this test runner, we'll assume the main Settings
# has a DATABASE_URL field that will be populated by this.
# If not, the DB connection will fail.
# A better way for Settings would be:
# DATABASE_URL: str = os.environ.get("DATABASE_URL_FOR_RUNNER", "sqlite+aiosqlite:///./default_app.db")
# This modification should ideally be in app.core.config.py, but for the runner we just set the var.
os.environ["DB_HOST"] = "." # Required by Settings, but not used by SQLite URL
os.environ["DB_PORT"] = "0" # Required by Settings
os.environ["DB_USER"] = "user"    # Required by Settings
os.environ["DB_PASSWORD"] = "pass"  # Required by Settings
os.environ["DB_NAME"] = DATABASE_FILE_PATH # Required by Settings
os.environ["GOOGLE_API_KEY"] = "test_google_api_key" # Required by Settings, for A1/A2/B/D if reached

# Adjust imports based on actual final location of modules
try:
    from app.services.orchestration import start_session_processing_pipeline
    from app.core.config import Settings, get_settings # Import get_settings
    from app.models.data_models import LearningSessionInput
    from app.db.database import SessionLocal, Base, engine # Import Base and engine for table creation
    from app.db import crud, models as db_models
    # from app.db.init_db import init_db_dev # init_db_dev might be too complex for direct call here
except ImportError as e:
    print(f"ImportError: {e}. Make sure PYTHONPATH is set correctly or script is run from project root.")
    print("Attempting to add project root to sys.path for this run...")
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
    from app.services.orchestration import start_session_processing_pipeline
    from app.core.config import Settings, get_settings
    from app.models.data_models import LearningSessionInput
    from app.db.database import SessionLocal, Base, engine
    from app.db import crud, models as db_models
    # from app.db.init_db import init_db_dev

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("OrchestrationTestRunner")

# Use a modified Settings class locally if just for APP_TEMP_DIR and not for DB/Xunfei
# However, orchestration.py receives settings, so the one from get_settings() will be used.
# The environment variables set above should ensure get_settings() loads the test credentials.

APP_TEMP_DIR_FOR_RUNNER = Path("./temp_orchestration_run_files_runner")

async def main():
    logger.info("Starting orchestration test.")
    
    # Settings will be loaded via get_settings() using the env vars set above.
    settings_for_test = get_settings()
    
    # Use a specific temp dir for files created *by the runner itself*, if any.
    # Orchestration.py's tempfile.mkdtemp() will use system default temp locations.
    os.makedirs(APP_TEMP_DIR_FOR_RUNNER, exist_ok=True)
    logger.info(f"Runner script temp dir: {APP_TEMP_DIR_FOR_RUNNER.resolve()}")


    # Create tables for SQLite if they don't exist.
    # This is crucial for CRUD operations to succeed.
    logger.info(f"Using database: {engine.url}")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created (if they didn't exist).")
    except Exception as e_db_create:
        logger.error(f"Error creating database tables: {e_db_create}")
        # Depending on the DB type and error, this might be fatal for the test.

    db = SessionLocal() # Uses the engine configured by env vars via get_settings()
    try:
        session_id = str(uuid.uuid4())
        video_id = str(uuid.uuid4()) 

        try:
            db_session_obj = db_models.LearningSession(
                session_id=session_id, 
                status="test_initiated", 
                user_id="cursor_test_runner",
                created_at=datetime.now() # Ensure created_at is set
            )
            db.add(db_session_obj)
            
            # Check if LearningSource model requires structured_transcript_segments_json and extracted_key_information_json
            # If so, provide defaults or ensure they are nullable.
            # For this test, assuming they are nullable or the DB schema allows defaults.
            db_source_obj = db_models.LearningSource(
                video_id=video_id, 
                session_id=session_id, 
                video_title="Bili Test Video by Runner",
                # source_type="bilibili_video", # This field may not exist in db_models.LearningSource
                original_url="https://www.bilibili.com/video/BV1QmG1zcE6x/",
                # Defaulting potentially non-nullable fields if schema requires them
                structured_transcript_segments_json='[]', # Default empty JSON array
                extracted_key_information_json='{}', # Default empty JSON object
                user_id="cursor_test_runner"
            )
            db.add(db_source_obj)
            db.commit()
            logger.info(f"Initial DB records created for session_id: {session_id}, video_id: {video_id}")
        except Exception as db_init_exc:
            logger.error(f"Failed to create initial DB records: {db_init_exc}")
            db.rollback() # Rollback on error
            # Not returning, as we want to see orchestration attempt and log its DB interaction issues.

        learning_input = LearningSessionInput(
            bilibili_video_url="https://www.bilibili.com/video/BV1QmG1zcE6x/",
            rawTranscriptText="", 
            initialVideoTitle="Bili Test Video (from URL)"
        )

        logger.info(f"Calling start_session_processing_pipeline for session_id: {session_id}")
        await start_session_processing_pipeline(
            db=db,
            session_id=session_id,
            video_id=video_id, 
            learning_session_input=learning_input,
            settings=settings_for_test # Pass the settings loaded via get_settings()
        )
        logger.info("Finished calling start_session_processing_pipeline.")

    except Exception as e:
        logger.exception(f"Error during orchestration test: {e}")
    finally:
        if db:
            db.close()
            logger.info("Database session closed.")
        
        if os.path.exists(APP_TEMP_DIR_FOR_RUNNER):
            import shutil
            try:
                shutil.rmtree(APP_TEMP_DIR_FOR_RUNNER)
                logger.info(f"Cleaned up runner script temp dir: {APP_TEMP_DIR_FOR_RUNNER}")
            except Exception as e_cleanup_runner:
                logger.warning(f"Failed to clean up runner temp dir {APP_TEMP_DIR_FOR_RUNNER}: {e_cleanup_runner}")
        
        if os.path.exists(DATABASE_FILE_PATH):
            try:
                os.remove(DATABASE_FILE_PATH)
                logger.info(f"Cleaned up test database: {DATABASE_FILE_PATH}")
            except Exception as e_cleanup_db:
                logger.warning(f"Failed to clean up test database {DATABASE_FILE_PATH}: {e_cleanup_db}")

if __name__ == "__main__":
    asyncio.run(main()) 