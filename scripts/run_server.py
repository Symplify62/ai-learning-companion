#!/usr/bin/env python3
"""
 启动服务器脚本
 
 该脚本使用uvicorn启动FastAPI应用服务器。
"""
import os
import sys
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

def run_server(host="127.0.0.1", port=8000, reload=True, log_level="info"):
    """
     使用uvicorn运行服务器
     
     @param host 主机地址
     @param port 端口号
     @param reload 是否启用热重载
     @param log_level 日志级别
    """
    import uvicorn
    
    print(f"启动AI学习伴侣系统API服务器 - 监听 {host}:{port}")
    print("按CTRL+C停止服务器")
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level
    )

def parse_args():
    """
     解析命令行参数
     
     @return 解析后的参数
    """
    parser = argparse.ArgumentParser(description="启动AI学习伴侣系统API服务器")
    
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="服务器主机地址 (默认: 127.0.0.1)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="服务器端口号 (默认: 8000)"
    )
    
    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="禁用热重载"
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["debug", "info", "warning", "error", "critical"],
        default="info",
        help="日志级别 (默认: info)"
    )
    
    return parser.parse_args()

if __name__ == "__main__":
    # 解析命令行参数
    args = parse_args()
    
    # 运行服务器
    run_server(
        host=args.host,
        port=args.port,
        reload=not args.no_reload,
        log_level=args.log_level
    ) 