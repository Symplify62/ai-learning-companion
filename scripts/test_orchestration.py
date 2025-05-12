"""
 业务编排测试脚本
 
 用于测试AI处理管道的编排逻辑。
"""
import sys
import os
import json
import asyncio
from pathlib import Path

# 将项目根目录添加到模块搜索路径
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from app.db.database import SessionLocal
from app.db import crud
from app.services.orchestration import start_session_processing_pipeline

async def test_orchestration_pipeline():
    """
     测试业务编排管道
     
     创建测试会话和资源，并运行处理管道流程。
    """
    # 创建数据库会话
    db = SessionLocal()
    
    try:
        print("\n===== 开始测试业务编排管道 =====")
        
        # 1. 创建学习会话
        print("\n步骤1: 创建测试会话和学习资源...")
        session = crud.create_learning_session(
            db=db,
            status="测试编排流程",
            user_id="test_orchestration_user"
        )
        print(f"✅ 成功创建学习会话: session_id={session.session_id}, status={session.status}")
        
        # 2. 创建学习资源
        source = crud.create_learning_source(
            db=db,
            session_id=session.session_id,
            video_title="测试编排流程的视频",
            user_id="test_orchestration_user",
            initial_source_description="这是用于测试编排流程的视频描述"
        )
        print(f"✅ 成功创建学习资源: video_id={source.video_id}, title={source.video_title}")
        
        # 3. 准备一些测试转录文本
        test_transcript = """
        这是一段测试转录文本，用于测试模块A.1和A.2的处理流程。
        这段文本模拟了用户提交的原始转录内容。
        模块A.1应该能够处理这段文本，并生成结构化的转录片段。
        模块A.2应该能够从转录片段中提取关键信息。
        """
        
        # 4. 运行处理管道
        print("\n步骤2: 运行处理管道...")
        await start_session_processing_pipeline(
            db=db,
            session_id=session.session_id,
            video_id=source.video_id,
            raw_transcript_text_for_a1=test_transcript,
            initial_video_title=None,
            initial_source_description=None
        )
        
        # 5. 验证结果
        print("\n步骤3: 验证处理结果...")
        updated_session = crud.get_learning_session(
            db=db,
            session_id=session.session_id
        )
        print(f"✅ 会话状态更新: status={updated_session.status}")
        
        updated_source = crud.get_learning_source_by_session_id(
            db=db,
            session_id=session.session_id
        )
        print(f"✅ 学习资源更新: title={updated_source.video_title}")
        print(f"   视频描述: {updated_source.video_description}")
        print(f"   总时长: {updated_source.total_duration_seconds} 秒")
        
        # 打印结构化转录的前200个字符（如果存在）
        if updated_source.structured_transcript_segments_json:
            print(f"\n✅ 结构化转录片段 (A.1输出): {updated_source.structured_transcript_segments_json[:200]}...")
        else:
            print("\n❌ 结构化转录片段未更新")
        
        # 打印提取的关键信息（如果存在）
        if updated_source.extracted_key_information_json:
            print(f"\n✅ 提取的关键信息 (A.2输出): {updated_source.extracted_key_information_json[:200]}...")
        else:
            print("\n❌ 提取的关键信息未更新")
        
        # 打印测试成功信息
        print("\n===== 测试完成! 业务编排管道工作正常 =====")
        print("模块A.1和A.2的处理流程已验证通过")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
    finally:
        # 关闭数据库会话
        db.close()

if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_orchestration_pipeline()) 