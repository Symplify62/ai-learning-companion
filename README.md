# AI Learning Companion System - Backend MVP

Backend services for the AI Learning Companion MVP.

## 项目描述

这是一个基于FastAPI的后端系统，用于支持AI学习伴侣系统。系统将提供API接口，支持移动和Web应用程序。
通过AI技术，将原始转录内容处理成结构化的学习笔记。

## 主要功能

- 接收原始文本转录
- 通过AI模块处理转录内容，包括：
  - 模块A.1: 转录预处理和元数据生成
  - 模块A.2: 关键信息提取
  - 模块B: 智能Markdown笔记生成
  - 模块D: 知识提示生成
- 提供API端点获取处理结果

## 系统架构

- **API层**: FastAPI路由和端点
- **服务层**: 业务逻辑和处理编排
- **AI模块**: 文本分析和笔记生成
- **数据访问层**: 数据库交互（使用SQLAlchemy ORM）
- **数据库**: MySQL/OceanBase

## 处理流程

系统处理流程如下：

1. 接收包含原始转录文本的请求
2. 创建学习会话和学习资源记录
3. 启动处理管道，按顺序执行：
   - 模块A.1：转录预处理和元数据生成
   - 模块A.2：关键信息提取
   - 模块B：智能Markdown笔记生成
   - 模块D：知识提示生成
4. 将处理结果保存到数据库
5. 提供API端点获取结果

## 环境要求

- Python 3.8+
- MySQL 8.0+ 或 OceanBase
- 环境变量（见下面配置部分）

## 安装指南

1. 克隆此仓库
2. 安装依赖：
   ```
   pip install -r requirements.txt
   ```
3. 复制环境变量模板并配置：
   ```
   cp env.example .env
   ```
   编辑 `.env` 文件，设置数据库连接参数

## 配置数据库

编辑 `.env` 文件，配置以下环境变量：

```
# 数据库设置
DB_HOST=localhost
DB_PORT=3306
DB_USER=yourusername
DB_PASSWORD=yourpassword
DB_NAME=ai_learning_companion
```

## 启动服务

使用提供的运行脚本：

```
python scripts/run_server.py
```

或者直接使用uvicorn：

```
uvicorn app.main:app --reload
```

## 测试系统

系统提供了两个测试脚本：

1. 内部处理流程测试：
   ```
   python scripts/test_complete_pipeline.py
   ```

2. API端点测试：
   ```
   python scripts/test_api_client.py
   ```

## API文档

启动服务后，访问 `/docs` 或 `/redoc` 获取完整API文档。API包括以下主要端点：

- `POST /api/v1/learning_sessions/` - 创建新的学习会话
- `GET /api/v1/learning_sessions/{session_id}` - 获取会话状态
- `GET /api/v1/learning_sessions/{session_id}/source` - 获取会话相关的学习资源
- `GET /api/v1/learning_sessions/{session_id}/notes` - 获取会话相关的生成笔记
- `GET /api/v1/learning_sessions/notes/{note_id}/knowledge_cues` - 获取笔记相关的知识提示
- `PATCH /api/v1/learning_sessions/{session_id}/status` - 更新会话状态 