#!/usr/bin/env python3
"""
 测试脚本：API客户端
 
 该脚本测试AI学习伴侣系统的API端点，
 通过HTTP请求创建学习会话并获取结果。
"""
import asyncio
import requests
import time
import json
from typing import Dict, Any, Optional, List

# API基础URL（根据实际运行环境调整）
BASE_URL = "http://localhost:8000"

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

def create_learning_session() -> Dict[str, Any]:
    """
     创建学习会话
     
     @return 创建的会话信息
    """
    print("创建学习会话...")
    
    # 定义请求数据
    data = {
        "rawTranscriptText": TEST_TRANSCRIPT,
        "initialVideoTitle": "API测试 - 机器学习基础",
        "initialSourceDescription": "API测试用转录内容"
    }
    
    # 发送POST请求
    response = requests.post(
        f"{BASE_URL}/api/v1/learning_sessions/",
        json=data
    )
    
    # 检查响应
    if response.status_code == 200:
        result = response.json()
        print(f"会话创建成功，ID: {result['sessionId']}")
        return result
    else:
        print(f"会话创建失败，状态码: {response.status_code}")
        print(f"错误信息: {response.text}")
        raise Exception("会话创建失败")

def get_session_status(session_id: str) -> Dict[str, Any]:
    """
     获取会话状态
     
     @param session_id 会话ID
     @return 会话状态信息
    """
    print(f"获取会话状态 (ID: {session_id})...")
    
    # 发送GET请求
    response = requests.get(
        f"{BASE_URL}/api/v1/learning_sessions/{session_id}"
    )
    
    # 检查响应
    if response.status_code == 200:
        result = response.json()
        print(f"会话状态: {result['status']}")
        return result
    else:
        print(f"获取会话状态失败，状态码: {response.status_code}")
        print(f"错误信息: {response.text}")
        raise Exception("获取会话状态失败")

def get_session_source(session_id: str) -> Optional[Dict[str, Any]]:
    """
     获取会话相关的学习资源
     
     @param session_id 会话ID
     @return 学习资源信息，如果不存在则返回None
    """
    print(f"获取会话学习资源 (ID: {session_id})...")
    
    # 发送GET请求
    response = requests.get(
        f"{BASE_URL}/api/v1/learning_sessions/{session_id}/source"
    )
    
    # 检查响应
    if response.status_code == 200:
        result = response.json()
        print(f"获取学习资源成功")
        print(f"视频标题: {result['video_title']}")
        return result
    elif response.status_code == 404:
        print("学习资源不存在或尚未处理完成")
        return None
    else:
        print(f"获取学习资源失败，状态码: {response.status_code}")
        print(f"错误信息: {response.text}")
        raise Exception("获取学习资源失败")

def get_session_notes(session_id: str) -> List[Dict[str, Any]]:
    """
     获取会话相关的生成笔记
     
     @param session_id 会话ID
     @return 笔记列表
    """
    print(f"获取会话笔记 (ID: {session_id})...")
    
    # 发送GET请求
    response = requests.get(
        f"{BASE_URL}/api/v1/learning_sessions/{session_id}/notes"
    )
    
    # 检查响应
    if response.status_code == 200:
        result = response.json()
        print(f"获取笔记成功，数量: {len(result)}")
        return result
    else:
        print(f"获取笔记失败，状态码: {response.status_code}")
        print(f"错误信息: {response.text}")
        raise Exception("获取笔记失败")

def get_note_knowledge_cues(note_id: str) -> List[Dict[str, Any]]:
    """
     获取笔记相关的知识提示
     
     @param note_id 笔记ID
     @return 知识提示列表
    """
    print(f"获取笔记知识提示 (ID: {note_id})...")
    
    # 发送GET请求
    response = requests.get(
        f"{BASE_URL}/api/v1/learning_sessions/notes/{note_id}/knowledge_cues"
    )
    
    # 检查响应
    if response.status_code == 200:
        result = response.json()
        print(f"获取知识提示成功，数量: {len(result)}")
        return result
    else:
        print(f"获取知识提示失败，状态码: {response.status_code}")
        print(f"错误信息: {response.text}")
        raise Exception("获取知识提示失败")

def poll_until_complete(session_id: str, timeout_seconds: int = 90) -> None:
    """
     轮询直到处理完成
     
     @param session_id 会话ID
     @param timeout_seconds 超时时间（秒）
    """
    print(f"开始轮询会话状态，等待处理完成...")
    
    start_time = time.time()
    completed_states = ["all_processing_complete", "knowledge_cues_generation_complete", "error_in_processing"]
    
    while True:
        # 检查是否超时
        if time.time() - start_time > timeout_seconds:
            print(f"轮询超时 ({timeout_seconds}秒)")
            break
        
        # 获取当前状态
        status_info = get_session_status(session_id)
        current_status = status_info["status"]
        
        # 检查是否完成
        if current_status in completed_states:
            print(f"处理已完成，最终状态: {current_status}")
            break
        
        # 等待一段时间后继续轮询
        print(f"当前状态: {current_status}，继续等待...")
        time.sleep(5)

def print_note_preview(note: Dict[str, Any]) -> None:
    """
     打印笔记预览
     
     @param note 笔记数据
    """
    print("\n=================== 笔记预览 ===================")
    print(f"笔记ID: {note['note_id']}")
    
    if note.get('summary_of_note'):
        print(f"摘要: {note['summary_of_note']}")
    
    # 显示关键概念
    if note.get('key_concepts_mentioned') and len(note['key_concepts_mentioned']) > 0:
        print(f"关键概念: {', '.join(note['key_concepts_mentioned'])}")
    
    # 显示预计阅读时间
    if note.get('estimated_reading_time_seconds'):
        minutes = note['estimated_reading_time_seconds'] // 60
        seconds = note['estimated_reading_time_seconds'] % 60
        print(f"预计阅读时间: {minutes}分{seconds}秒")
    
    # 显示内容预览（前300个字符）
    if note.get('markdown_content'):
        content_preview = note['markdown_content'][:300]
        if len(note['markdown_content']) > 300:
            content_preview += "..."
        print("\n内容预览:")
        print(content_preview)
    
    print("===============================================\n")

def print_knowledge_cues_preview(cues: List[Dict[str, Any]]) -> None:
    """
     打印知识提示预览
     
     @param cues 知识提示列表
    """
    if not cues:
        print("\n没有找到知识提示")
        return
        
    print(f"\n=================== 知识提示预览 ({len(cues)} 条) ===================")
    
    for i, cue in enumerate(cues[:3], 1):  # 最多显示3条
        print(f"\n[{i}] 难度: {cue['difficulty_level']}")
        print(f"问题: {cue['question_text']}")
        print(f"答案: {cue['answer_text']}")
        if cue.get('source_reference_in_note'):
            print(f"引用: {cue['source_reference_in_note']}")
    
    if len(cues) > 3:
        print(f"\n... 还有 {len(cues) - 3} 条知识提示未显示 ...")
    
    print("\n===============================================\n")

def main():
    """主函数"""
    print("开始API测试...")
    
    try:
        # 步骤1：创建学习会话
        session_info = create_learning_session()
        session_id = session_info["sessionId"]
        
        # 步骤2：轮询直到处理完成
        poll_until_complete(session_id)
        
        # 步骤3：获取处理结果
        source_info = get_session_source(session_id)
        if source_info:
            print("\n处理结果摘要:")
            print(f"视频ID: {source_info['video_id']}")
            print(f"视频标题: {source_info['video_title']}")
            print(f"视频描述: {source_info['video_description']}")
            print(f"是否有结构化转录: {source_info['has_structured_transcript']}")
            print(f"是否有提取的关键信息: {source_info['has_extracted_key_information']}")
        
        # 步骤4：获取生成的笔记
        notes = get_session_notes(session_id)
        note_id = None
        
        if notes and len(notes) > 0:
            print(f"\n获取到 {len(notes)} 条笔记")
            # 打印第一条笔记的预览
            note = notes[0]
            note_id = note["note_id"]
            print_note_preview(note)
        else:
            print("\n没有找到生成的笔记")
        
        # 步骤5：获取知识提示（如果有笔记）
        if note_id:
            cues = get_note_knowledge_cues(note_id)
            print_knowledge_cues_preview(cues)
            
        # 测试完成
        print("\nAPI测试完成!")
        
    except Exception as e:
        print(f"测试过程中出错: {str(e)}")

if __name__ == "__main__":
    main() 