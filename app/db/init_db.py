"""
 数据库初始化模块
 
 该模块负责初始化数据库，创建表结构。
"""
from app.db.database import Base, engine
from app.db import models

def init_db():
    """
     初始化数据库
     
     创建所有ORM模型对应的数据库表。
    """
    print("Creating all tables (if they don't exist)...")
    Base.metadata.create_all(bind=engine) # 创建数据库表
    print("Database tables check/creation complete.")

if __name__ == "__main__":
    print("Initializing database (running as script)...")
    init_db()
    print("Database initialization script finished.") 