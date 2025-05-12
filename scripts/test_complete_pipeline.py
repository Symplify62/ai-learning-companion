#!/usr/bin/env python3
"""
 测试脚本：完整处理流程
 
 该脚本测试AI学习伴侣系统的完整处理流程，
 包括创建学习会话、处理原始转录文本、生成笔记等。
"""
import sys
import asyncio
import json
import time
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.db import crud
from app.services.orchestration import start_session_processing_pipeline

# 测试用的转录文本
TEST_TRANSCRIPT = """
这是一个测试转录内容。这个转录文件包含了一些关于机器学习基础概念的讲解。
首先，机器学习是人工智能的一个子领域，主要关注如何让计算机程序从数据中学习和改进。
机器学习的基本类型包括监督学习、无监督学习和强化学习。
在监督学习中，模型从标记的训练数据中学习，然后对新数据进行预测。
无监督学习则处理无标记数据，尝试找出其中的结构或模式。
强化学习是通过与环境互动来学习如何达到目标。
机器学习在各个领域都有广泛应用，包括自然语言处理、计算机视觉、推荐系统等。
"""

async def test_complete_pipeline():
    """测试完整处理流程"""
    print("开始测试完整处理流程...")
    
    # 创建数据库会话
    db = SessionLocal()
    
    try:
        # 步骤1: 创建学习会话
        print("步骤1: 创建学习会话...")
        db_session = crud.create_learning_session(
            db=db,
            status="testing_initiated",
            user_id=None
        )
        session_id = db_session.session_id
        print(f"创建的会话ID: {session_id}")
        
        # 步骤2: 创建学习资源
        print("步骤2: 创建学习资源...")
        db_source = crud.create_learning_source(
            db=db,
            session_id=session_id,
            video_title="测试视频 - 机器学习基础",
            initial_source_description="机器学习基础概念讲解视频",
            user_id=None
        )
        video_id = db_source.video_id
        print(f"创建的视频ID: {video_id}")
        
        # 步骤3: 启动处理管道 (这里我们直接调用，而不是作为后台任务)
        print("步骤3: 启动处理管道...")
        # 在实际应用中，这通常会通过BackgroundTasks进行处理
        await start_session_processing_pipeline(
            db, 
            session_id, 
            video_id, 
            TEST_TRANSCRIPT
        )
        
        # 步骤4: 验证处理结果
        print("步骤4: 验证处理结果...")
        
        # 4.1 验证会话状态
        updated_session = crud.get_learning_session(db, session_id)
        print(f"会话最终状态: {updated_session.status}")
        
        # 4.2 验证学习资源内容
        updated_source = crud.get_learning_source_by_session_id(db, session_id)
        print(f"视频标题: {updated_source.video_title}")
        print(f"视频描述: {updated_source.video_description}")
        
        # 转换JSON字符串为Python对象以便查看
        if updated_source.structured_transcript_segments_json:
            transcript_segments = json.loads(updated_source.structured_transcript_segments_json)
            print(f"结构化转录片段数量: {len(transcript_segments)}")
        
        if updated_source.extracted_key_information_json:
            key_info = json.loads(updated_source.extracted_key_information_json)
            print(f"提取的关键信息项数量: {len(key_info)}")
        
        # 4.3 验证生成的笔记
        notes = crud.get_notes_by_session_id(db, session_id)
        if notes:
            print(f"生成的笔记数量: {len(notes)}")
            for note in notes:
                print(f"笔记ID: {note.note_id}")
                print(f"笔记摘要: {note.summary_of_note}")
                # 笔记内容太长，只打印前100个字符
                print(f"笔记内容预览: {note.markdown_content[:100]}...")
        else:
            print("未找到生成的笔记")
            
        print("测试完成!")
            
    except Exception as e:
        print(f"测试过程中出错: {str(e)}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    # 运行异步测试函数
    asyncio.run(test_complete_pipeline()) 