# /Users/alec/Downloads/ai_learning_companion_mvp/test_direct_session_local.py

import sys
import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session

# 将项目根目录的app目录添加到Python的模块搜索路径中
# 这样我们就可以使用像 from app.db.database import SessionLocal 这样的导入
# 注意: 根据您的项目结构和运行脚本的方式，可能需要调整此路径
# 如果您是从项目根目录运行 python test_direct_session_local.py，这个路径应该是对的
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(project_root)) # 将根目录加入，这样app.db.database可以被找到

# 首先加载 .env 文件，因为数据库URL的构建依赖于环境变量
# 确保 .env 文件在项目根目录
if load_dotenv(os.path.join(project_root, ".env")):
    print(".env file loaded successfully.")
else:
    print("Warning: .env file not found or not loaded. Database connection might fail if credentials are not set elsewhere.")

# 现在尝试导入 SessionLocal 和一个模型
try:
    from app.db.database import SessionLocal  # SessionLocal 在 database.py 中定义
    from app.db.models import LearningSession # 导入一个模型用于测试查询
    print("Successfully imported SessionLocal and LearningSession model.")
except ImportError as e:
    print(f"Error importing SessionLocal or LearningSession model: {e}")
    print("Please check your PYTHONPATH or the import path in this script.")
    sys.exit(1)

def run_test():
    print("\nAttempting to use SessionLocal directly...")
    db: Session = None # Initialize db to None
    try:
        print("1. Creating a new database session using SessionLocal()...")
        db = SessionLocal()
        print("   Session created successfully.")

        print("\n2. Attempting a simple query (e.g., count LearningSession records)...")
        # 您可以选择一个适合您数据库当前状态的简单查询
        # 如果 LearningSession 表可能为空，first() 比 count() 更简单，不会因为空表报错
        first_session_record = db.query(LearningSession).first()
        
        if first_session_record:
            print(f"   Successfully queried database. First session found - ID: {first_session_record.session_id}, Status: {first_session_record.status}")
        else:
            # 这仍然表示连接和查询是成功的，只是表里可能没数据或查询没匹配到
            count = db.query(LearningSession).count()
            print(f"   Successfully queried database. LearningSession table contains {count} records (first() returned None).")
        
        print("\nTest finished: SessionLocal appears to be working correctly!")

    except Exception as e:
        print(f"\nError during SessionLocal test: {e}")
        import traceback
        traceback.print_exc() # 打印完整的异常信息
    finally:
        if db:
            print("\nClosing database session...")
            db.close()
            print("Session closed.")

if __name__ == "__main__":
    run_test()