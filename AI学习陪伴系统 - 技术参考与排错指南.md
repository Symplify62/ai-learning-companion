# AI学习陪伴系统 - 技术参考与排错指南 (Technical Reference & Troubleshooting Guide)

**文档版本：** 1.1 (云端部署初步完成后更新)
**基于状态：** 迭代一核心功能完成，并已初步部署到云端 (Render + Vercel + OceanBase Cloud) (截至 [请在此处填写当前日期，例如：2025年5月12日])
**核心贡献者：** Alec (项目发起人/核心用户), ADC v1.3 (前任), ADC v1.4 (现任)
**目标读者：** AI开发协调员 (ADC), 技术开发者

---

## 1. 引言与文档目的

本文档旨在为“AI学习陪伴系统”项目提供一份详尽的技术参考和问题排查指南。它深入介绍了项目的技术架构、代码结构、核心模块实现细节、云端部署配置，以及在开发、部署和运行过程中可能遇到的常见问题及其定位和解决策略。

本文档的目标是帮助技术参与者（特别是新任ADC）快速理解系统的技术实现和云端部署状态，能够有效地进行后续开发、维护和问题排查。它整合了截至云端部署初步完成后的最新技术状态和调试经验。

---

## 2. 技术架构与选型概览 (云端部署初步完成后)

*   **后端 (Backend):**
    *   **框架:** Python 3.12, FastAPI
    *   **ORM & 数据校验:** SQLAlchemy, Pydantic
    *   **数据库:** OceanBase Cloud (MySQL 兼容模式, 通过标准 `mysql-connector-python` 驱动访问)
    *   **数据库连接池:** SQLAlchemy Engine 配置 (当前使用默认配置，可按需在 `app/db/database.py` 中为 `create_engine` 添加 `pool_pre_ping=True`, `pool_recycle=1800` 等参数以增强稳定性)。
    *   **异步处理:** FastAPI `BackgroundTasks`, `asyncio` (包括 `asyncio.to_thread` 用于包装同步IO密集型任务如ASR)。
    *   **部署平台:** Render (通过 Docker 部署)。
*   **前端 (Frontend):**
    *   **框架/库:** React (v19+), Vite (构建工具)。
    *   **核心依赖:** `react-markdown` (用于渲染笔记)。
    *   **部署平台:** Vercel。
*   **AI模型:**
    *   **语音转写 (ASR):** 讯飞语音识别大模型 (长音频转写服务)。
    *   **笔记与知识点生成:** Google Gemini 1.5 Flash (通过API调用)。
*   **核心外部工具依赖 (在 Docker 镜像中安装):**
    *   `yt-dlp`: 用于下载B站视频 (通过 `subprocess` 调用)。
    *   `ffmpeg`: 用于音频提取与转换 (通过 `subprocess` 调用)。
*   **配置管理:**
    *   **后端 (Render):** 通过 Render 平台的环境变量设置。代码中通过 `app/core/config.py` (Pydantic `Settings`) 读取。
    *   **前端 (Vercel):** 通过 Vercel 平台的环境变量设置 (`VITE_API_BASE_URL`)。

---

## 3. 项目文件结构详解 (主要变更和新增)

### 3.1. 项目根目录 (例如：`/Users/alec/Downloads/ai_learning_companion_mvp/`)

*   **`Dockerfile` (新增):** 用于构建后端 FastAPI 应用的 Docker 镜像，供 Render 部署使用。包含 Python 环境、系统依赖 (`ffmpeg`, `yt-dlp`) 和应用代码的打包。
*   **`app/`**: 后端FastAPI应用程序的核心代码。
*   **`frontend_web/`**: 前端React (Vite构建) 应用程序的代码。
*   **`scripts/`**: 辅助脚本。
*   **`.env` (本地使用):** (位于根目录) **本地开发时**使用的后端环境变量配置文件。**通过 `.gitignore` 忽略，不入库。** 云端配置通过 Render 平台环境变量。
*   **`requirements.txt`**: 后端Python依赖列表。**关键依赖：`fastapi`, `uvicorn[standard]` (或 `uvicorn`), `sqlalchemy`, `pydantic`, `mysql-connector-python`, `google-generativeai`, 等。确保 `psycopg2-binary` 已被移除。**
*   **`.gitignore`**: 配置 Git 忽略规则，确保敏感文件和不必要的目录（如 `node_modules`, `__pycache__`, 本地 `.env`）不被提交。
*   **`frontend_web/package.json`**: 前端依赖和脚本定义。
*   **`frontend_web/.env` (本地使用):** (位于`frontend_web`目录) **本地开发时**使用的前端环境变量配置文件 (主要配置 `VITE_API_BASE_URL` 指向本地后端)。云端配置通过 Vercel 平台环境变量。
*   **`debug_imports.py` (临时调试文件，已删除):** 此文件曾用于调试 Render 部署时的导入问题，在问题解决后已从项目中移除并从 Git 中删除。如遇类似底层启动问题，可参考其逻辑创建新的调试脚本。

---
**问题排查与优化指引 (根目录级别)：**
*   **环境配置错误 (云端):**
    *   **根源**: Render 或 Vercel 平台环境变量设置错误或缺失。
        *   Render (后端): `DATABASE_URL`, `GOOGLE_API_KEY`, `XUNFEI_APPID`, `XUNFEI_SECRET_KEY` 格式或值错误。
        *   Vercel (前端): `VITE_API_BASE_URL` 未指向正确的 Render 后端 URL。
    *   **排查**: 仔细检查 Render/Vercel 控制台的环境变量设置；查看应用启动日志（后端）或浏览器网络请求（前端）。
*   **依赖问题 (Docker 构建时):**
    *   **根源**: `requirements.txt` 依赖项无法安装或版本冲突。
    *   **排查**: 查看 Render 构建日志中 `pip install -r requirements.txt` 的输出。
*   **ImportError (Python - 云端):**
    *   **根源**: 模块导入路径错误；依赖未在 `requirements.txt` 中声明导致未安装到 Docker 镜像中 (如我们曾遇到的 `psycopg2` 问题，后确认为应使用 `mysql-connector-python`)。
    *   **排查**: 查看 Render 应用运行时日志。使用临时调试脚本（类似已删除的 `debug_imports.py` 的逻辑）或在 Dockerfile `CMD` 中直接运行 Python 命令进行测试。
---

### 3.2. 后端结构详解 (`app/`) - 主要变更点

#### 3.2.1. `app/main.py`
*   **职责**: FastAPI应用入口点。
*   **关键逻辑 (新增/修改):**
    *   **顶层 `print` 语句 (用于调试，部署稳定后可考虑移除或改为日志库输出)：** `print("--- Python interpreter is reading app/main.py ---")`，用于确认文件在容器启动时被读取。
    *   **`on_startup` 事件处理器：**
        *   调用 `create_db_tables()` 函数，在应用启动时自动检查并创建数据库表。
        *   包含详细的 `try-except Exception as e:` 错误捕获和 `traceback.print_exc()`，以便在日志中显示详细的启动错误。
        *   包含 `print` 语句记录启动流程的关键节点 (如 "Attempting to create database tables...", "Database tables checked/created successfully.")。

#### 3.2.2. `app/core/config.py`
*   **`Settings` 类 (Pydantic `BaseSettings`) (已修改):**
    *   **移除了**单独的 `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` 字段。
    *   **新增了 `DATABASE_URL: str` 字段**，用于直接接收完整的数据库连接字符串。其注释已更新，指明其应为 MySQL/OceanBase 格式，例如: `"mysql+mysqlconnector://user:pass@host:port/db"`。
    *   其他字段 (API密钥等) 保留不变。
    *   `Config` 子类中 `env_file = ".env"` 主要影响本地开发，云端部署依赖平台注入的环境变量。

#### 3.2.3. `app/db/database.py`
*   **SQLAlchemy `engine` 创建逻辑 (已修改):**
    *   直接使用 `settings.DATABASE_URL` (从 `app.core.config.get_settings()`) 来创建 `engine`。
        ```python
        # 示例，具体代码可能略有不同
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker, declarative_base # declarative_base 可能在这里或 models.py
        from app.core.config import get_settings

        settings = get_settings()
        engine = create_engine(
            settings.DATABASE_URL
            # 考虑添加连接池参数以提高生产环境稳定性:
            # pool_pre_ping=True,
            # pool_recycle=1800 # 例如30分钟
        )
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base = declarative_base() # 或者从 models.py 导入 Base

        def get_db():
            db = SessionLocal()
            try:
                yield db
            finally:
                db.close()
        ```
    *   移除了之前可能存在的通过拼接独立数据库组件环境变量来构造 URL 的逻辑。

#### 3.2.4. `app/db/models.py`
*   **数据类型调整 (已修改):**
    *   对于需要存储大量文本的字段（如 `LearningSource.structured_transcript_segments_json`, `GeneratedNote.markdown_content`），已统一使用 **`sqlalchemy.dialects.mysql.LONGTEXT`** 以适配 OceanBase (MySQL 兼容模式)。
    *   确保 `from sqlalchemy.dialects.mysql import LONGTEXT` 已导入。
    *   移除了对 `psycopg2` 或 PostgreSQL 特定类型的依赖。
*   **`created_at` 字段 (新增):**
    *   为核心模型 (`LearningSession`, `LearningSource`, `GeneratedNote`, `KnowledgeCue`) 添加了 `created_at = Column(DateTime, default=func.now())` 字段，用于记录创建时间。
    *   确保 `from sqlalchemy.sql import func` 和 `from sqlalchemy import DateTime, Column` 等已导入。

---

## 4. 云端部署配置详解

### 4.1. 后端部署 (Render)

*   **部署方式：** 通过 Docker。
*   **`Dockerfile`：**
    *   使用多阶段构建 (`python:3.12-slim` 基础镜像)。
    *   `builder` 阶段：安装 `ffmpeg` (通过 `apt-get`)，安装 `requirements.txt` 中的 Python 依赖 (确保包含 `mysql-connector-python`，不含 `psycopg2-binary`)，安装 `yt-dlp` (通过 `pip`)。
    *   `final` 阶段：安装 `ffmpeg`，从 `builder` 阶段复制已安装的 Python 包 (`site-packages`) 和 `yt-dlp` 可执行文件，复制 `app` 目录。
    *   `EXPOSE 8000`。
    *   `CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "debug"]` (使用 `python -m uvicorn` 并开启 debug 日志级别以方便调试)。
*   **Render 服务配置：**
    *   **Environment:** Docker。
    *   **Branch:** `main` (或您的主开发分支)。
    *   **Instance Type:** Free (注意其资源限制和可能因不活动而导致的休眠策略，首次访问休眠服务可能较慢)。
    *   **Environment Variables (关键):**
        *   `DATABASE_URL`: 指向 OceanBase Cloud 的 MySQL 格式连接字符串。
            *   **格式:** `mysql+mysqlconnector://<user>:<password>@<host>:<port>/<database_name>`
            *   **示例:** `mysql+mysqlconnector://alec:YOUR_PASSWORD@obmt6pebuta1j0qo-mi.aliyun-cn-hangzhou-internet.oceanbase.cloud:3306/ai_learning_companion_db`
            *   **SSL/TLS 注意：** 当前配置依赖 `mysql-connector-python` 的默认 SSL 行为。如果 OceanBase Cloud 强制特定 SSL 模式或需要客户端证书/CA，则需要在 `DATABASE_URL` 中添加相应的 SSL 参数 (如 `?ssl_ca=...`, `&ssl_cert=...`, `&ssl_key=...`, `&tls_versions=...` 等)。这需要查阅 OceanBase Cloud 和 `mysql-connector-python` 文档，并可能需要将证书文件打包到 Docker 镜像或使用 Render Secret Files。
        *   `GOOGLE_API_KEY`: 您的 Google Gemini API 密钥。
        *   `XUNFEI_APPID`: 您的讯飞 App ID。
        *   `XUNFEI_SECRET_KEY`: 您的讯飞 Secret Key。
        *   `PORT`: `8000` (与 Dockerfile 和 Uvicorn 命令一致)。
    *   **Auto-Deploy:** 建议开启 "Yes"，这样推送到 GitHub 仓库的指定分支后会自动部署。

### 4.2. 前端部署 (Vercel)

*   **部署方式：** 连接 GitHub 仓库。
*   **Vercel 项目配置：**
    *   **Framework Preset:** Vite (或 React)。
    *   **Root Directory:** `frontend_web` (确保 Vercel 在此子目录中查找前端项目)。
    *   **Build Command:** 通常为 `npm run build` (或 `yarn build`，取决于项目)。
    *   **Output Directory:** 通常为 `dist` (相对于 `frontend_web`)。
    *   **Environment Variables (关键):**
        *   `VITE_API_BASE_URL`: 指向部署在 Render 上的后端服务的 URL (例如 `https://your-render-app-name.onrender.com`，**不带末尾斜杠**)。

### 4.3. 数据库配置 (OceanBase Cloud)

*   **网络访问控制 (白名单):**
    *   通过系统变量 `ob_tcp_invited_nodes` 控制。
    *   **必须修改此变量以允许 Render 服务器的 IP 连接。**
    *   最简单的测试设置是 `%` (允许任何 IP)，命令：`SET GLOBAL ob_tcp_invited_nodes='%';` (在 `sys` 租户以 `root` 用户或有权限用户执行)。
    *   **安全警告：** 长期使用 `%` 存在安全风险。应尽可能配置更严格的 IP 范围，或研究 Render 是否提供可用于白名单的静态出口 IP 地址（通常付费服务提供此类功能）。
*   **SSL/TLS：**
    *   OceanBase 支持 SSL/TLS 加密传输。
    *   如上所述，当前部署依赖默认行为。如果连接因 SSL 问题失败，需要根据 OceanBase Cloud 的具体要求（如CA证书、客户端证书/密钥、特定TLS版本或加密套件）来配置 `DATABASE_URL` 中的 SSL 参数。
*   **用户权限：**
    *   连接数据库的用户 (当前为 `alec`) 必须拥有对目标数据库 (`ai_learning_companion_db`) 的 `CREATE TABLE`, `SELECT`, `INSERT`, `UPDATE`, `DELETE` 等必要权限。

---

## 5. 核心数据流概要 (云端部署后)

1.  **前端 (Vercel)**: 用户在浏览器中访问 Vercel URL -> 输入B站URL/文本 -> 点击提交 -> JavaScript 发送 `POST` 请求到 `VITE_API_BASE_URL` (即 Render 后端 URL) 的 `/api/v1/learning_sessions/` 端点。
2.  **后端API (Render)**: FastAPI 应用接收请求 -> 校验输入 -> 创建初始 `LearningSession` 记录到 OceanBase Cloud (状态 `PROCESSING_INITIATED`) -> 使用 `BackgroundTasks` 异步调度 `start_session_processing_pipeline`。
3.  **前端 (Vercel)**: 收到 `session_id` -> 启动轮询，向 Render 后端发送 `GET /api/v1/learning_sessions/{session_id}/status` 请求。
4.  **后端编排服务 (Render - `orchestration.py` 后台任务)**:
    *   执行视频下载 (`yt-dlp`)、音频处理 (`ffmpeg`)、ASR (讯飞)、AI模块链调用 (Gemini)。
    *   每次关键步骤后，通过 SQLAlchemy 将状态和结果更新/保存到 OceanBase Cloud 数据库中。
    *   所有数据库操作通过局部、短生命周期的 SQLAlchemy 会话进行，并包含 `commit`/`rollback`/`close`。**确保 `orchestration.py` 中有充分的日志记录数据库操作的尝试、成功或失败。**
5.  **前端 (Vercel)**: 根据从 Render 后端获取的 `/status` 响应，更新界面显示。当状态为 `ALL_PROCESSING_COMPLETE` 时，显示最终结果。

---

## 6. 通用问题排查策略 (云端部署后总结)

1.  **从日志入手 (Render & Vercel & 浏览器 DevTools)：**
    *   **Render (后端):**
        *   **部署日志 (Events/Deploys):** 查看 Docker 镜像构建过程 (`Dockerfile` 解析、`apt-get`、`pip install`)、容器启动命令执行情况。
        *   **运行时日志 (Logs):** 查看 FastAPI/Uvicorn 应用日志，包括我们添加的 `print` 语句、Python Traceback、数据库错误等。**当前 Uvicorn 日志级别已设为 `debug`，有助于捕获更多信息。**
    *   **Vercel (前端):**
        *   **部署日志:** 查看前端构建过程 (`npm install`, `npm run build`)。
        *   **运行时 (浏览器):** 使用浏览器开发者工具 (DevTools) 的 "Console" 查看 JavaScript 错误，"Network" 查看 API 请求是否发往正确的 Render 后端 URL，以及请求/响应内容和状态码。
2.  **明确问题范围：** 前端 UI vs 前端 API 调用 vs 后端 API 接口 vs 后端后台服务 vs 数据库连接/操作 vs AI 模块调用？
3.  **检查配置与环境变量 (关键)：**
    *   Render: `DATABASE_URL` (方言 `mysql+mysqlconnector`, 凭证, 主机, 端口, 数据库名, SSL参数？), API 密钥。
    *   Vercel: `VITE_API_BASE_URL` (确保指向 Render 后端，无尾部斜杠)。
    *   OceanBase Cloud: 白名单 (`ob_tcp_invited_nodes`)，SSL/TLS 配置，用户权限。
4.  **验证外部服务连通性：**
    *   **数据库连接：** 这是最常见的故障点。确保 Render 容器可以访问 OceanBase Cloud。
    *   AI 服务 (Gemini, 讯飞)：API 密钥是否有效，是否有网络访问限制。
5.  **代码与环境一致性：**
    *   `requirements.txt` 是否包含了所有必要的驱动和库 (特别是 `mysql-connector-python`，确保没有 `psycopg2-binary` 残留)。
    *   SQLAlchemy 模型定义 (`LONGTEXT`, `created_at`) 是否与目标数据库 (OceanBase/MySQL) 兼容。
    *   Python 版本 (Dockerfile 中指定)。
    *   **文件路径大小写敏感性：** Linux (Docker 环境) 区分大小写，macOS (开发环境) 默认不区分。确保所有代码中的文件名、模块名引用与实际大小写一致。
6.  **逐步调试与简化：**
    *   **`Dockerfile` `CMD` 修改：**
        *   使用 `CMD ["env"]` 检查环境变量是否按预期传递到容器。
        *   使用 `CMD ["python", "your_debug_script.py"]` (可参考已删除的 `debug_imports.py` 逻辑创建) 逐步测试导入和核心功能，特别是配置加载和数据库引擎初始化。
    *   **简化应用逻辑：** 在 `app/main.py` 的 `on_startup` 中临时注释掉复杂操作（如数据库表创建），逐步恢复以定位问题。
    *   在代码关键路径（如 `orchestration.py` 的数据库操作前后，AI模块调用前后）添加详细 `print` 或标准库 `logging` 语句。
7.  **数据库模式同步问题 (如 `Unknown column ...`)：**
    *   **症状：** `(mysql.connector.errors.ProgrammingError) 1054 (42S22): Unknown column '...' in 'field list'` 或类似错误。
    *   **原因：** SQLAlchemy 模型定义与实际数据库表结构不一致 (例如，模型中有 `created_at`，但数据库表中没有)。
    *   **解决方案：**
        *   **对于新部署或数据可丢弃的情况：** 在 OceanBase 中删除相关表，让应用启动时通过 `Base.metadata.create_all()` 根据最新模型重新创建。
        *   **对于已有数据的环境：** 使用 `ALTER TABLE ... ADD COLUMN ...` 等 SQL 语句手动修改 OceanBase 中的表结构，使其与模型匹配。
        *   **长期方案：** 引入数据库迁移工具 (如 Alembic)。
8.  **SSL/TLS 连接问题 (针对 OceanBase)：**
    *   **症状：** 连接数据库时报 SSL 错误、握手失败、证书验证失败、`SSL connection has been closed unexpectedly` (虽然此错误也可能由其他原因引起，如连接池问题)。
    *   **排查：**
        *   确认 OceanBase Cloud 服务器端 SSL/TLS 配置（是否强制、认证方式、TLS 版本）。
        *   在 `DATABASE_URL` 中添加正确的 SSL 参数 (如 `ssl_ca`, `ssl_cert`, `ssl_key`, `ssl_disabled`, `tls_versions` 等，具体参数和值需查阅 `mysql-connector-python` 和 OceanBase 文档)。
        *   如果需要证书文件，确保它们已正确打包到 Docker 镜像中（通过 `COPY` 指令），并在 `DATABASE_URL` 中使用正确的容器内路径引用。或者使用 Render 的 "Secret Files" 功能管理证书。
9.  **Render `Exited with status 128` (或其他非零退出码) 且无应用日志：**
    *   **Dockerfile 解析错误：** `Dockerfile` 本身存在语法错误（如我们遇到的将 `print` 语句误加到 `Dockerfile`）。检查 Render 构建日志的早期阶段。
    *   **`CMD` 执行失败：** `CMD` 指定的命令无法启动或立即崩溃。
        *   尝试更简单的 `CMD` (如 `CMD ["ls", "-la", "/app"]` 或 `CMD ["python", "--version"]`) 来验证容器基本运行环境。
        *   确保 `CMD` 中的可执行文件路径正确且在容器的 `PATH` 中。
        *   使用 `python -m uvicorn ...` 可能比直接 `uvicorn ...` 提供更明确的 Python 环境上下文。
    *   **底层依赖问题：** Python 解释器或 `uvicorn` 依赖了某个在 `python:3.12-slim` 基础镜像中缺失或不兼容的底层系统库（可能性较低，但存在）。

---

本文档 (v1.1) 已根据云端部署到 Render (后端 Docker + OceanBase Cloud) 和 Vercel (前端) 的经验进行了更新。随着项目的演进，应持续维护和补充本文档。