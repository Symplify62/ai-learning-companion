# AI学习陪伴系统 - 技术参考与排错指南 (Technical Reference & Troubleshooting Guide)

**文档版本：** 1.1 (整合版)
**基于状态：** 迭代一核心功能完成并优化部署 (截至 2024年5月15日)
**核心贡献者：** Alec (项目发起人/核心用户), ADC v1.3 (前任), ADC v1.4 (现任)
**目标读者：** AI开发协调员 (ADC), 技术开发者

---

## 1. 引言与文档目的

本文档旨在为"AI学习陪伴系统"项目提供一份详尽的技术参考和问题排查指南。它深入介绍了项目的技术架构、代码结构、核心模块实现细节以及在开发和运行过程中可能遇到的常见问题及其定位和解决策略。

本文档的目标是帮助技术参与者（特别是新任ADC）快速理解系统的技术实现，能够有效地进行后续开发、维护和问题排查。它整合了迭代一完成后的最新技术状态和调试经验。

---

## 2. 技术架构与选型概览 (迭代一完成后)

*   **后端 (Backend):**
    *   **框架:** Python 3.12, FastAPI
    *   **ORM & 数据校验:** SQLAlchemy, Pydantic
    *   **数据库:** PostgreSQL (生产环境), OceanBase/MySQL (开发环境可选)
    *   **数据库连接池:** SQLAlchemy Engine 配置 `pool_pre_ping=True`, `pool_recycle=1800`
    *   **异步处理:** FastAPI `BackgroundTasks`, `asyncio` (包括 `asyncio.to_thread` 用于包装同步IO密集型任务如ASR)
*   **前端 (Frontend):**
    *   **框架/库:** React (v19+), Vite (构建工具)
    *   **核心依赖:** `react-markdown` (用于渲染笔记)
*   **AI模型:**
    *   **语音转写 (ASR):** 讯飞语音识别大模型 (长音频转写服务)
    *   **笔记与知识点生成:** Google Gemini 1.5 Flash (通过API调用)
*   **核心外部工具依赖:**
    *   `yt-dlp`: 用于下载B站视频 (通过 `subprocess` 调用)
    *   `ffmpeg`: 用于音频提取与转换 (通过 `subprocess` 调用)
*   **配置管理:**
    *   后端: `.env` 文件 + Pydantic `Settings` (`app/core/config.py`)
    *   前端: `frontend_web/.env` 文件 + Vite环境变量 (`import.meta.env`)
*   **部署:**
    *   **容器化:** Docker 多阶段构建 (python:3.12-slim)
    *   **应用服务器:** Uvicorn (通过 `python -m uvicorn` 启动，增强启动日志)

---

## 3. 项目文件结构详解

### 3.1. 项目根目录 (`/Users/alec/Downloads/ai_learning_companion_mvp/`)

*   **`app/`**: 后端FastAPI应用程序的核心代码。
*   **`frontend_web/`**: 前端React (Vite构建) 应用程序的代码。
*   **`scripts/`**: 辅助脚本 (如API测试的 `curl` 命令)。
*   **`bili2text/`**: (历史遗留，核心功能已内化，不再直接使用)。
*   **`.env`**: (位于根目录) **后端**环境变量配置文件 (数据库URL, Google Key, 讯飞凭证)。**极其重要，不入库。**
*   **`requirements.txt`**: 后端Python依赖列表。**需确保已安装。**
*   **`frontend_web/package.json`**: 前端依赖和脚本定义。**需确保已安装。**
*   **`frontend_web/.env`**: (位于`frontend_web`目录) **前端**环境变量配置文件 (主要配置 `VITE_API_BASE_URL`)。

---
**问题排查与优化指引 (根目录级别)：**
*   **环境配置错误**:
    *   **根源**: `app/.env` (后端) 或 `frontend_web/.env` (前端) 文件错误或缺失。
        *   后端: `DATABASE_URL`, `GOOGLE_API_KEY`, `XUNFEI_APPID`, `XUNFEI_SECRET_KEY` 错误。
        *   前端: `VITE_API_BASE_URL` 错误。
    *   **排查**: 检查 `.env` 文件内容；查看应用启动日志（后端）或浏览器网络请求（前端）。
*   **依赖问题**:
    *   **根源**: `requirements.txt` 或 `frontend_web/package.json` 依赖未安装或版本冲突。
    *   **排查**: 确保已运行 `pip install -r requirements.txt` 和 `npm install`。检查终端报错。
*   **ImportError (Python)**:
    *   **根源**: 模块导入路径错误，循环导入。
    *   **排查**: 检查FastAPI启动时的 `ImportError` 堆栈跟踪。确认 `get_settings()` 使用方式正确（替换旧的全局 `settings` 导入）。
*   **Docker部署问题**:
    *   **根源**: Dockerfile 配置错误；环境变量未正确传递；容器内外网络配置不匹配。
    *   **排查**: 查看Docker构建和运行日志；使用 `--log-level debug` 增强Uvicorn日志；在关键文件开头添加调试 `print`。
*   **数据库兼容性问题**:
    *   **根源**: 数据库方言不兼容（如MySQL特有类型用于PostgreSQL）；连接字符串格式错误。
    *   **排查**: 检查 SQLAlchemy 模型类型；确保使用通用类型（如 `Text` 而非 `LONGTEXT`）；验证连接字符串格式。
---

### 3.2. 后端结构详解 (`app/`)

#### 3.2.1. `app/main.py`
*   **职责**: FastAPI应用入口点。初始化FastAPI实例，挂载API路由器 (`app.api.v1.api.api_router`)。配置启动事件用于自动创建数据库表。
*   **状态**: 稳定可用，增强了错误处理和启动日志。
---
**问题排查与优化指引 (`app/main.py`)：**
*   **应用无法启动**:
    *   **根源**: 路由器挂载错误、全局依赖问题、数据库连接失败、表创建错误。
    *   **排查**: 查看uvicorn启动时的终端错误输出（设置 `--log-level debug`）；检查文件开头的诊断 `print` 输出；查看 `on_startup` 和 `create_db_tables` 函数的错误处理日志。
*   **数据库表自动创建失败**:
    *   **根源**: 数据库连接问题；SQLAlchemy模型与数据库方言不匹配；权限不足。
    *   **排查**: 检查 `on_startup` 事件中 `create_db_tables` 的错误日志；验证 `DATABASE_URL` 格式和凭证；确认模型使用了与数据库兼容的类型。
---

#### 3.2.2. `app/core/` (核心配置与工具)
*   **`config.py`**:
    *   **职责**: 应用配置管理。使用Pydantic `Settings`模型从 `.env` 加载和验证配置。提供 `get_settings()` 函数获取缓存配置实例。
    *   **包含字段**: `DATABASE_URL`, `GOOGLE_API_KEY`, `XUNFEI_APPID: str | None`, `XUNFEI_SECRET_KEY: str | None` 等。
    *   **配置**: `Settings.Config` 中 `extra = 'ignore'` 允许 `.env` 中存在未定义字段。
    *   **状态**: 稳定可用。
*   **`enums.py` (新增)**:
    *   **职责**: 定义枚举类型。
    *   **核心内容**: `ProcessingStatus(str, Enum)` 定义了所有详细处理状态。
    *   **状态**: 已实现并全面应用。
*   **`utils.py` (新增)**:
    *   **职责**: 通用工具函数。
    *   **核心内容**: `normalize_bilibili_url` 标准化B站URL。
    *   **状态**: 已实现并集成。
---
**问题排查与优化指引 (`app/core/`)：**
*   **配置加载失败 (`config.py`)**:
    *   **根源**: `Settings` 模型字段与 `.env` 变量名/类型不匹配；`get_settings()` 未正确返回实例；讯飞凭证未在 `.env` 中定义或加载失败。
    *   **排查**: 应用启动时的Pydantic验证错误；确保 `.env` 变量名与 `Settings` 字段匹配。
*   **ImportError (`enums.py`, `utils.py`)**:
    *   **根源**: 其他模块无法正确导入这些文件中的内容。
    *   **排查**: 检查 `from app.core... import ...` 语句是否正确。
---

#### 3.2.3. `app/api/v1/endpoints/learning_sessions.py` (API端点 - 已增强)
*   **职责**: 定义学习会话相关API端点。处理HTTP请求，调用服务层逻辑（通过 `BackgroundTasks`），返回响应。
*   **`POST /api/v1/learning_sessions/` (已更新)**:
    *   **输入**: `LearningSessionInput` (Pydantic模型, `bilibili_video_url` 和 `rawTranscriptText` 至少提供一个)。
    *   **逻辑**: 校验输入 -> 创建初始数据库记录 (`crud.create_learning_session`, 状态 `PROCESSING_INITIATED`) -> **使用 `BackgroundTasks` 异步启动 `orchestration.start_session_processing_pipeline` (不再传递 `db` 参数)**。
    *   **响应**: `LearningSessionResponse` (含 `session_id`, 初始状态)。
*   **`GET /{session_id}/status` (已增强)**:
    *   **逻辑**: 调用 `crud.get_learning_session` 等获取数据 -> 组装 `LearningSessionDetail`。
    *   **响应**: `LearningSessionDetail`。`status` 字段返回细化状态字符串。当状态为 `ALL_PROCESSING_COMPLETE` 时，`final_results` (`FinalResultsPayload`) 包含 **`ai_generated_video_title`**, **`plain_transcript_text`**, **`timestamped_transcript_segments`**, 以及原有的 `notes` 和 `knowledge_cues`。
*   **状态**: 已增强并验证。
---
**问题排查与优化指引 (`app/api/v1/endpoints/learning_sessions.py`)：**
*   **API返回错误 (4xx/5xx)**:
    *   **根源**: 请求体验证失败 (`LearningSessionInput` 约束)；服务层后台任务异常；API端点自身逻辑错误；`Settings` 注入/使用错误。
    *   **排查**: 查看FastAPI错误响应和后端日志；使用API测试工具；确认 `Depends(get_settings)` 使用；检查 `BackgroundTasks` 参数。
*   **数据完整性问题 (结果不全/不正确)**:
    *   **根源**: `read_learning_session_status` 组装 `FinalResultsPayload` 逻辑错误；未能从DB正确获取或处理 `LearningSource` 数据；`FinalResultsPayload` 模型定义与填充逻辑不一致。
    *   **排查**: 调试 `read_learning_session_status`；检查DB数据；确认Pydantic模型定义。
*   **后台任务未按预期启动/执行**:
    *   **根源**: `BackgroundTasks.add_task` 调用问题；`start_session_processing_pipeline` 早期快速失败未留日志。
    *   **排查**: 检查 `add_task` 参数；在 `start_session_processing_pipeline` 入口加日志。
---

#### 3.2.4. `app/services/orchestration.py` (核心编排服务 - 已重大重构)
*   **职责**: 核心AI处理管道编排器。协调视频下载、音频处理、ASR、AI模块链调用。**内部管理数据库会话生命周期。**
*   **核心函数 `start_session_processing_pipeline` (已重构)**:
    *   **签名**: 无 `db: Session` 参数。主要参数 `session_id`, `video_id`, `learning_session_input`, `settings`。
    *   **数据库会话管理 (关键变更)**:
        *   导入 `SessionLocal`。
        *   **为每个（或每组）DB操作创建局部、短生命周期会话 (`db_local: Session = SessionLocal()`)**。
        *   使用 `try...except...finally` 确保 `commit()` / `rollback()` / `close()`。
        *   使用辅助函数 `_update_status_in_session`, `_get_session_in_session` 封装局部会话逻辑。
    *   **状态管理**: 全面使用 `ProcessingStatus` 枚举更新状态。
    *   **ASR服务调用 (已解耦)**: 通过 `get_asr_service` 获取 `AbstractAsrService` 实例，调用 `await asr_client.transcribe(...)`。
    *   **B站视频处理流程**: `yt-dlp` 下载 -> `audio_processor.prepare_audio_for_asr` -> 解耦的ASR服务 -> **ASR结果直接适配为A.1输入格式**。
    *   **AI模块链调用**: 串行异步调用A.1, A.2, B, D。结果通过局部会话CRUD持久化。
    *   **错误处理**: 主 `try...except` 捕获异常并记录错误状态。
    *   **临时文件管理**: 使用 `tempfile.mkdtemp()`, `finally` 中清理。
*   **状态**: 已完成核心重构、优化，并通过端到端测试验证。**文件较大，未来可拆分。**
---
**问题排查与优化指引 (`app/services/orchestration.py`)：**
*   **AI处理流程中断/结果错误**:
    *   **根源**: 逻辑错误 (模块调用顺序, 数据传递, 状态更新)；**数据库操作失败 (检查局部会话创建/关闭/提交/回滚)**；`settings` 内容错误；AI模块调用失败未处理；`yt-dlp`/`ffmpeg` 调用失败；ASR服务调用失败。
    *   **排查**: **依赖详细日志输出** (追踪 `session_id`, 状态, 出入参, 异常)；确认函数签名无 `db` 参数；确认所有CRUD使用 `db_local` 并正确关闭；确认 `ProcessingStatus` 使用正确。
*   **ImportError**: 检查新增导入 (`SessionLocal`, `ProcessingStatus`, `get_asr_service`, `AbstractAsrService`) 是否正确。
---

#### 3.2.5. `app/ai_modules/` (AI模块核心逻辑与Prompt)
*   **`prompts_module_*.py`**: 存储System Prompt文本。
    *   **`prompts_module_a1.py`**: `SYSTEM_PROMPT_A1_V1_1` 已迭代至 **v1.4** (优化忠实度、分段、流畅性、标点如《》)。
    *   **`prompts_module_b.py`**: 模块B Prompt 已迭代至 **v1.3** (去H1标题、语言一致性、元数据稳定)。
    *   `prompts_module_d.py`: 支持动态数量和难度级别提示。
*   **`module_*_llm_caller.py`**: 封装调用Google Gemini API逻辑。
    *   接受 `settings: Settings` 获取 `GOOGLE_API_KEY`。
    *   **`module_b_llm_caller.py`**: 含LLM响应JSON必需字段校验。
    *   `module_d_llm_caller.py`: `temperature=0.75`, 处理可变数量和难度。
*   **状态**: Prompts已优化验证，调用器工作正常。
---
**问题排查与优化指引 (`app/ai_modules/`)：**
*   **AI输出质量不高/格式错误/内容不准确**:
    *   **根源**: Prompt问题 (指令不清/冲突/LLM未遵循)；LLM调用参数 (temperature)；输入数据质量。
    *   **排查/优化**: **迭代修改System Prompt** (调整措辞/约束/示例/强调)；调整LLM参数；分析上游输入；**在Python调用端做严格校验和日志记录**；接受LLM能力边界。
*   **AI模块调用失败 (HTTP错误/限流/认证)**:
    *   **根源**: 网络问题；`GOOGLE_API_KEY` 无效/超限；Gemini API服务问题；响应解析错误。
    *   **排查**: 检查调用器错误捕获和日志；确认API Key有效性；查看LLM原始响应；参考Gemini文档。
---

#### 3.2.6. `app/db/` (数据库交互核心)
*   **`models.py` (SQLAlchemy ORM模型)**:
    *   定义 `LearningSession`, `LearningSource`, `GeneratedNote`, `KnowledgeCue` 等。
    *   `LearningSession.status` (`String(50)`)。
    *   **对于大文本/JSON字段使用通用 `Text` 类型（已从MySQL特有的 `LONGTEXT` 迁移）。**
    *   `LearningSource.video_title_ai` (或 `video_title`)。
    *   `relationship` 定义。
    *   **状态**: 已优化为PostgreSQL兼容，稳定可用。
*   **`crud.py` (数据访问操作)**:
    *   实现CRUD。
    *   `create_learning_session`, `update_learning_session_status` 接受 `ProcessingStatus` 枚举。
    *   新增 `get_learning_source_by_video_id`。
    *   **状态**: 已更新并稳定运作。
*   **`database.py` (数据库引擎与会话工厂)**:
    *   **使用单一 `DATABASE_URL` 环境变量构建连接字符串。**
    *   `engine` 配置 `pool_pre_ping=True`, `pool_recycle=1800`。
    *   `SessionLocal` (`sessionmaker`) 定义。
    *   **状态**: 已优化并验证。
*   `session.py` (或类似): 定义 `get_db` 依赖注入函数 (主要用于API层)。
---
**问题排查与优化指引 (`app/db/`)：**
*   **数据库操作错误/数据不一致**:
    *   **根源**: ORM模型与表结构不符；CRUD逻辑错误；数据库连接URL错误；**（已重点优化）连接失效**；事务管理不当 (当前由`orchestration.py`局部会话管理)；**数据库方言不兼容问题（如MySQL特有类型）**。
    *   **排查**: 检查SQLAlchemy错误日志；确认DB URL和凭证；验证 `orchestration.py` 局部会话管理模式实现；**确保模型使用通用SQL类型，避免数据库特定类型**。
*   **数据库性能问题**:
    *   **关注点**: 查询效率 (索引缺失/复杂JOIN)；大量数据写入/更新。
    *   **优化**: 添加索引；优化查询；分批处理。
*   **数据库表创建/迁移问题**:
    *   **根源**: 自动表创建失败；字段类型不兼容；缺少表创建权限。
    *   **排查**: 检查 `app/main.py` 中的表创建日志；验证 `Base.metadata.create_all` 是否被正确调用；确认数据库用户权限。
---

#### 3.2.7. `app/models/data_models.py` (Pydantic数据模型 - 已更新)
*   **职责**: 定义API请求/响应模型及内部数据传递模型。
*   **主要更新**:
    *   使用 `ProcessingStatus` 枚举。
    *   `LearningSessionInput.rawTranscriptText` 可选。
    *   `FinalResultsPayload` 新增 `ai_generated_video_title`, `plain_transcript_text`, `timestamped_transcript_segments`。
    *   包含 `LearningSessionResponse`, `LearningSessionDetail`, `NoteWithCues` 等。
*   **状态**: 已更新并与API响应一致。
---
**问题排查与优化指引 (`app/models/data_models.py`)：**
*   **数据校验失败 (FastAPI 422错误)**:
    *   **根源**: 请求体JSON与输入模型不符；响应数据与输出模型不符。
    *   **排查**: 阅读422错误 `detail`；确保模型类型提示正确；确认 `model_config = {'from_attributes': True}` (如需)。
*   **API响应缺少字段/为 `null`**:
    *   **根源**: 模型字段为 `Optional` 且无值；API端点组装响应逻辑错误。
    *   **排查**: 检查API端点填充逻辑；确认上游数据源包含数据。
---

#### 3.2.8. `app/utils/transcript_parser.py`
*   **职责**: 解析用户直接粘贴的原始文本转录稿。
*   **使用场景**: 主要用于 `rawTranscriptText` 输入路径。B站流程不经过此解析器。
*   **状态**: 功能稳定，未大改。
---
**问题排查与优化指引 (`app/utils/transcript_parser.py`)：**
*   **转录稿解析错误 (原始文本输入路径)**:
    *   **根源**: 输入文本格式与解析预期不符。
    *   **排查**: 调试 `parse_raw_transcript_to_segments`；考虑增加格式兼容性。
---

#### 3.2.9. `app/services/xunfei_asr_service.py` (讯飞ASR客户端 - 已重构)
*   **职责**: 讯飞ASR服务具体实现。
*   **核心类 `XunfeiLfasrClient` (已更新)**:
    *   **实现 `AbstractAsrService` 接口**。
    *   `async def transcribe(...)` 使用 `asyncio.to_thread()` 调用内部同步转写逻辑 `_perform_synchronous_transcription`。
*   **依赖**: `requests`。
*   **状态**: 已重构并验证。
---
**问题排查与优化指引 (`app/services/xunfei_asr_service.py`)：**
*   **讯飞API调用失败**: 网络问题；API凭证无效/配置错误；讯飞API错误；音频文件问题。**检查 `__init__` 和工厂函数是否正确传递凭证。**
*   **转写结果不准确**: 讯飞模型本身限制；音频质量。
*   **异步封装问题**: `asyncio.to_thread` 使用不当；同步方法错误未正确传递/处理。
---

#### 3.2.10. `app/utils/audio_processor.py`
*   **职责**: 音频处理工具，核心 `prepare_audio_for_asr` 使用 `ffmpeg` 转换音频。
*   **状态**: 稳定可用。
---
**问题排查与优化指引 (`app/utils/audio_processor.py`)：**
*   **音频处理失败/效果不佳**: `ffmpeg` 命令错误/参数问题/输入文件问题。
*   **依赖问题**: 系统未安装 `ffmpeg` 或无法调用。
---

#### 3.2.11. `app/services/asr/` (ASR抽象层 - 新增)
*   **`base.py`**: 定义 `AbstractAsrService(ABC)` 及 `async def transcribe` 抽象方法。
*   **`factory.py`**: 定义 `get_asr_service(settings: Settings)` 工厂函数，返回 `AbstractAsrService` 实例 (当前为 `XunfeiLfasrClient`)。
*   **状态**: 已实现并集成。
---
**问题排查与优化指引 (`app/services/asr/`)：**
*   **ImportError**: 检查 `factory.py` 和 `orchestration.py` 的导入语句。
*   **工厂逻辑错误**: (未来若支持多种ASR) 检查基于配置选择客户端的逻辑。
*   **接口与实现不匹配**: 检查具体客户端的 `transcribe` 方法是否符合接口定义。
---

### 3.3. 前端结构详解 (`frontend_web/`)

#### 3.3.1. `frontend_web/src/components/BiliUrlSubmitForm.jsx` (核心UI组件)
*   **职责**: MVP主界面。负责URL输入、API请求发送 (`POST /learning_sessions/`)、加载状态管理、**状态轮询 (`GET /status`) 与友好展示**、**最终结果展示** (AI标题、两种转写稿、`react-markdown`渲染笔记、知识点)。
*   **技术**: React Hooks (`useState`, `useEffect`), `fetch` API。
*   **状态**: 核心功能闭环已在本地测试通过。
---
**问题排查与优化指引 (`frontend_web/src/components/BiliUrlSubmitForm.jsx`)：**
*   **URL提交失败/无响应**: 后端API未运行/地址错误 (`VITE_API_BASE_URL`)；网络问题；CORS；请求体构造错误。**排查: 浏览器DevTools Network/Console；后端日志。**
*   **状态轮询不工作/显示不正确**: `useEffect` 依赖问题；`fetchStatus` 逻辑错误；`statusDisplayMap` 映射缺失；定时器未清除。**排查: Console日志跟踪；Network检查 `/status` 请求/响应。**
*   **最终结果不显示/不全/格式错误**: API `/status` 响应 `final_results` 不完整；前端解析/渲染逻辑错误；`react-markdown` 问题；CSS问题。**排查: Network检查最终响应；Console打印 `resultsData`；React DevTools；调试JSX。**
*   **前端性能问题**: API轮询过频/未停止；大量结果渲染卡顿 (未来关注)。**优化: 合理轮询间隔；确保 `useEffect` 清理；考虑虚拟化。**
---

#### 3.3.2. `frontend_web/.env` (前端环境变量)
*   **职责**: 配置前端环境变量。
*   **核心配置**: **`VITE_API_BASE_URL`** (指向后端API)。
*   **重要性**: **必须正确配置并重启Vite开发服务器。**
---
**问题排查与优化指引 (`frontend_web/.env`)：**
*   **前端无法连接后端**: `.env` 文件缺失/语法错误；`VITE_API_BASE_URL` 变量名/值错误；未重启Vite。**排查: 确认文件内容；重启Vite；DevTools Network检查请求URL。**
---

## 4. 核心数据流概要 (B站视频处理路径)

1.  **前端 (`BiliUrlSubmitForm.jsx`)**: 用户输入B站URL -> 点击提交 -> 发送 `POST /api/v1/learning_sessions/` 请求 (含URL)。
2.  **后端API (`learning_sessions.py`)**: 接收请求 -> 校验输入 -> 创建 `LearningSession` 记录 (状态 `PROCESSING_INITIATED`) -> 使用 `BackgroundTasks` 调度 `start_session_processing_pipeline` (传递 `session_id`, `video_id`, `input`, `settings`) -> 返回 `session_id`。
3.  **前端**: 收到 `session_id` -> 启动轮询 `GET /api/v1/learning_sessions/{session_id}/status`。
4.  **后端编排服务 (`orchestration.py` - 后台任务)**:
    *   `normalize_bilibili_url`。
    *   **(循环/步骤，每次操作前后使用局部DB会话更新状态)**
    *   更新状态: `BILI_DOWNLOAD_ACTIVE`。
    *   `yt-dlp` 下载视频。
    *   更新状态: `AUDIO_EXTRACTION_ACTIVE`。
    *   `audio_processor.prepare_audio_for_asr` 提取/转换音频。
    *   更新状态: `ASR_PROCESSING_ACTIVE`。
    *   `get_asr_service` 获取ASR实例 -> `await asr_client.transcribe()`。
    *   更新状态: `A1_PREPROCESSING_ACTIVE`。
    *   适配ASR结果 -> 调用模块A.1 (`invoke_module_a1_llm`)。
    *   保存A.1结果 (结构化转写稿, AI标题) 到 `LearningSource`。
    *   更新状态: `A2_PROCESSING_ACTIVE`。
    *   调用模块A.2。
    *   保存A.2结果。
    *   更新状态: `B_NOTE_GENERATION_ACTIVE`。
    *   调用模块B (`invoke_module_b_llm`)。
    *   保存笔记 (`GeneratedNote.markdown_content`)。
    *   更新状态: `D_CUE_GENERATION_ACTIVE`。
    *   调用模块D (`invoke_module_d_llm`)。
    *   保存知识点 (`KnowledgeCue`)。
    *   更新状态: `ALL_PROCESSING_COMPLETE`。
    *   (若出错，更新为相应错误状态如 `ERROR_ASR_FAILED`)。
    *   清理临时文件。
5.  **前端**: 轮询 `/status` API，根据返回的 `status` 字符串，从 `statusDisplayMap` 显示友好提示。
6.  **前端**: 当轮询到 `status` 为 `ALL_PROCESSING_COMPLETE` 时，从响应的 `final_results` 中获取所有数据 (`ai_generated_video_title`, `plain_transcript_text`, `timestamped_transcript_segments`, `notes`, `knowledge_cues`) 并渲染到界面。

---

## 5. 通用问题排查策略 (总结)

1.  **从日志入手**: 
    * **后端**: Uvicorn日志 (`--log-level debug`)、FastAPI错误、SQLAlchemy异常、自定义 `print` 和 `traceback`
    * **前端**: 浏览器DevTools (Console/Network)
    * **容器**: Docker构建和运行日志、容器内应用日志

2.  **明确问题范围**: 
    * 前端UI vs API调用? 
    * 后端API vs 后台服务? 
    * DB vs AI模块? 
    * 配置 vs 代码依赖? 
    * 本地环境 vs 容器部署?
    * **关注重点维护区域**: ASR抽象层、数据库兼容性、状态枚举、`orchestration.py` 局部会话、Docker容器设置

3.  **排查环境与配置问题**:
    * **后端配置**: `.env` 文件 (DB连接、API密钥、ASR凭证)
    * **前端配置**: `frontend_web/.env` (`VITE_API_BASE_URL`)
    * **数据库连接**: PostgreSQL与MySQL连接字符串格式、兼容性、表自动创建
    * **容器配置**: 环境变量传递、网络设置、存储卷挂载

4.  **数据库兼容性检查**:
    * 确保SQLAlchemy模型使用通用类型 (`Text` 替代 `LONGTEXT`)
    * 验证数据库操作没有使用特定数据库方言功能
    * 检查表创建权限和过程

5.  **应用启动问题排查**:
    * 在核心文件开头添加 `print` 语句确认解释器读取流程
    * 提高Uvicorn日志级别 (`--log-level debug`)
    * 检查启动事件和表创建过程的异常处理

6.  **快速诊断方法**:
    * 使用 `/db-test` API快速检查数据库连接
    * 尝试 `python -m uvicorn` 替代直接 `uvicorn` 命令
    * 利用 `traceback.print_exc()` 获取详细堆栈信息
    * 临时修改 Dockerfile CMD 或编写简单的调试脚本在容器内运行

---

本文档提供了截至迭代一完成和优化部署后的详细技术参考和排错指南。随着项目的演进，应持续更新本文档以反映最新的技术状态和问题排查经验。

### 3.4. Docker部署 (新增)

#### 3.4.1. `Dockerfile` (多阶段构建)
*   **职责**: 定义容器化应用的构建和运行环境。
*   **构建阶段 (builder)**:
    *   基于 `python:3.12-slim`。
    *   安装 `ffmpeg` 和依赖。
    *   安装 Python 依赖和 `yt-dlp`。
*   **最终阶段 (final)**:
    *   从构建阶段复制 Python 环境和 `yt-dlp`。
    *   复制应用代码 (`app` 目录)。
    *   配置启动命令: `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level debug`。
*   **状态**: 稳定可用，已优化启动日志级别。
---
**问题排查与优化指引 (`Dockerfile`)：**
*   **构建失败**:
    *   **根源**: 依赖安装错误；系统依赖缺失；复制命令错误。
    *   **排查**: 查看 Docker 构建日志；确认 `apt-get` 和 `pip` 命令正确；验证文件路径。
*   **启动失败/静默失败**:
    *   **根源**: 环境变量缺失；数据库连接问题；应用代码错误；uvicorn 命令参数错误。
    *   **排查**: 使用 `--log-level debug` 提高日志级别；通过 `print` 语句在关键点添加调试输出；确认环境变量正确传递；尝试 `python -m uvicorn` 替代直接 `uvicorn` 命令。
*   **容器内外部通信问题**:
    *   **根源**: 端口映射错误；网络配置不当；跨容器通信问题。
    *   **排查**: 确认端口映射 (`-p 8000:8000`)；检查 API Base URL 配置；验证容器网络设置。
---

### 3.5. 环境变量与配置 (新增)

#### 3.5.1. 后端环境变量 (`.env`)
*   **职责**: 配置后端应用的关键参数。
*   **核心变量**:
    *   `DATABASE_URL`: 数据库连接字符串 (如 `postgresql://user:pass@host:port/dbname`)。
    *   `GOOGLE_API_KEY`: Google Gemini API 密钥。
    *   `XUNFEI_APPID`/`XUNFEI_SECRET_KEY`: 讯飞 ASR 服务凭证。
*   **状态**: 必须正确配置才能运行。
---
**问题排查与优化指引 (`.env`)：**
*   **配置加载失败**:
    *   **根源**: 文件不存在；格式错误；变量名不匹配；路径问题。
    *   **排查**: 确认 `.env` 文件存在且格式正确；验证变量名与 `app/core/config.py` 中 `Settings` 模型匹配；检查日志中的配置错误。
*   **数据库连接失败**:
    *   **根源**: `DATABASE_URL` 格式错误；凭证无效；数据库不可访问；PostgreSQL/MySQL 连接字符串格式不同。
    *   **排查**: 验证连接字符串格式是否正确（对应目标数据库类型）；确认数据库服务运行；测试连接（如使用 `app/main.py` 中的 `/db-test` API）。
---

#### 3.5.2. 前端环境变量 (`frontend_web/.env`)
*   **职责**: 配置前端应用的连接参数。
*   **核心变量**:
    *   `VITE_API_BASE_URL`: 指向后端 API 的 URL (如 `http://localhost:8000/api/v1`)。
*   **状态**: 必须正确配置并重启 Vite 服务器。
---
**问题排查与优化指引 (`frontend_web/.env`)：**
*   **API 连接失败**:
    *   **根源**: URL 格式错误；后端服务不可用；CORS 问题；未重启 Vite。
    *   **排查**: 确认 URL 格式和可访问性；验证后端服务运行；检查浏览器控制台网络和错误日志；**修改后重启 Vite 服务器**。
---