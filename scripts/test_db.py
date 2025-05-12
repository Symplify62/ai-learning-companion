"""
 数据库测试脚本
 
 用于测试数据库连接和CRUD操作。
"""
import sys
import os
import json
from pathlib import Path

# 将项目根目录添加到模块搜索路径
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from app.db.database import SessionLocal
from app.db import crud

def test_database_operations():
    """
     测试数据库操作
     
     创建学习会话和学习资源记录，并验证创建是否成功。
    """
    # 创建数据库会话
    db = SessionLocal()
    
    try:
        print("正在测试数据库连接和CRUD操作...")
        
        # 1. 创建学习会话
        session = crud.create_learning_session(
            db=db,
            status="测试状态",
            user_id="test_user_001"
        )
        print(f"✅ 成功创建学习会话: session_id={session.session_id}, status={session.status}")
        
        # 2. 创建学习资源
        source = crud.create_learning_source(
            db=db,
            session_id=session.session_id,
            video_title="测试视频标题",
            user_id="test_user_001",
            initial_source_description="测试视频描述"
        )
        print(f"✅ 成功创建学习资源: video_id={source.video_id}, title={source.video_title}")
        
        # 3. 获取会话
        retrieved_session = crud.get_learning_session(
            db=db,
            session_id=session.session_id
        )
        print(f"✅ 成功获取学习会话: session_id={retrieved_session.session_id}, status={retrieved_session.status}")
        
        # 4. 获取会话的所有资源
        sources = crud.get_learning_sources_by_session(
            db=db,
            session_id=session.session_id
        )
        print(f"✅ 成功获取学习资源列表: 数量={len(sources)}")
        
        # 5. 获取会话的单个资源
        single_source = crud.get_learning_source_by_session_id(
            db=db,
            session_id=session.session_id
        )
        print(f"✅ 成功获取单个学习资源: video_id={single_source.video_id}, title={single_source.video_title}")
        
        # 6. 更新会话状态
        updated_session = crud.update_learning_session_status(
            db=db,
            session_id=session.session_id,
            status="已处理"
        )
        print(f"✅ 成功更新学习会话状态: session_id={updated_session.session_id}, status={updated_session.status}")
        
        # 7. 使用A.1模块结果更新资源
        structured_transcript = {
            "segments": [
                {"start": 0, "end": 10, "text": "这是第一段文本"},
                {"start": 11, "end": 20, "text": "这是第二段文本"}
            ]
        }
        updated_source_a1 = crud.update_learning_source_after_a1(
            db=db,
            video_id=source.video_id,
            video_title_ai="AI优化的视频标题",
            video_description_ai="AI生成的视频描述",
            source_description_ai="AI生成的资源描述",
            total_duration_seconds_ai=120.5,
            structured_transcript_segments_json=json.dumps(structured_transcript, ensure_ascii=False)
        )
        print(f"✅ 成功使用A.1模块结果更新资源: video_id={updated_source_a1.video_id}, title={updated_source_a1.video_title}")
        
        # 8. 使用A.2模块结果更新资源
        key_information = {
            "key_concepts": ["概念1", "概念2"],
            "important_points": ["重点1", "重点2"]
        }
        updated_source_a2 = crud.update_learning_source_after_a2(
            db=db,
            video_id=source.video_id,
            extracted_key_information_json=json.dumps(key_information, ensure_ascii=False)
        )
        print(f"✅ 成功使用A.2模块结果更新资源: video_id={updated_source_a2.video_id}")
        print(f"   提取的关键信息: {updated_source_a2.extracted_key_information_json}")
        
        # 打印测试成功信息
        print("\n所有测试通过！数据库连接和CRUD操作正常。")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
    finally:
        # 关闭数据库会话
        db.close()

if __name__ == "__main__":
    # 检查数据库文件是否存在
    if os.path.exists("./ai_learning_companion.db"):
        print("检测到现有数据库文件。")
    else:
        print("未检测到现有数据库文件，将自动创建。")
    
    # 运行测试
    test_database_operations() 