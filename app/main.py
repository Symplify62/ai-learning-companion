from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.api.v1.endpoints import learning_sessions
from app.db.database import get_db, engine
from app.db.init_db import init_db
from app.db.models import Base

app = FastAPI(
    title="AI Learning Companion System",
    description="Backend API for the AI Learning Companion System",
    version="0.1.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境应限制为特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含路由
app.include_router(
    learning_sessions.router,
    prefix="/api/v1/learning_sessions",
    tags=["learning_sessions"]
)

@app.get("/")
async def root():
    """
     根路径响应
     
     @return 欢迎信息
    """
    return {"message": "欢迎使用AI学习伴侣系统API"}

@app.get("/db-test")
def test_db_connection(db: Session = Depends(get_db)):
    """
     测试数据库连接
     
     @param db 数据库会话（通过依赖注入）
     @return 连接状态信息
    """
    try:
        # 使用text()函数包装SQL查询
        db.execute(text("SELECT 1"))
        return {"status": "success", "message": "数据库连接成功"}
    except Exception as e:
        return {"status": "error", "message": f"数据库连接失败: {str(e)}"}

def create_db_tables():
    """
    检查并创建所有数据库表（如不存在）。
    """
    print("Attempting to create database tables if they don't exist...")
    try:
        Base.metadata.create_all(bind=engine)
        print("Database tables checked/created successfully.")
    except Exception as e:
        print(f"Error creating database tables: {e}")

# 注册启动事件，确保数据库表创建
@app.on_event("startup")
async def on_startup():
    create_db_tables()
