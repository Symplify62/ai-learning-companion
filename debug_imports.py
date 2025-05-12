print("--- Starting debug_imports.py ---")

print("Attempting to import Settings from app.core.config...")
try:
    from app.core.config import get_settings
    settings = get_settings()
    print(f"Successfully imported and instantiated Settings.")
    print(f"DATABASE_URL from settings: {settings.DATABASE_URL}")
    # You can add more settings to print if needed, e.g., settings.GOOGLE_API_KEY
except Exception as e:
    print(f"ERROR importing or instantiating Settings: {e}")
    import traceback
    traceback.print_exc() # Print full traceback

print("\nAttempting to import engine from app.db.database...")
try:
    from app.db.database import engine
    print(f"Successfully imported engine.")
    print(f"Engine URL: {str(engine.url)}")
except Exception as e:
    print(f"ERROR importing engine: {e}")
    import traceback
    traceback.print_exc()

print("\nAttempting to import Base and models from app.db.models...")
try:
    from app.db.models import Base # Assuming Base is your declarative base
    # You can try importing specific models too if Base itself doesn't trigger issues
    # from app.db.models import LearningSession # Example
    print(f"Successfully imported Base from app.db.models.")
except Exception as e:
    print(f"ERROR importing Base or models: {e}")
    import traceback
    traceback.print_exc()

print("\nAttempting to import FastAPI app instance from app.main...")
try:
    from app.main import app # Assuming 'app' is your FastAPI instance
    print(f"Successfully imported FastAPI app instance.")
except Exception as e:
    print(f"ERROR importing FastAPI app instance: {e}")
    import traceback
    traceback.print_exc()

print("--- Finished debug_imports.py ---") 