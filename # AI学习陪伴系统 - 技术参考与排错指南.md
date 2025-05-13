# AI学习陪伴系统 - 技术参考与排错指南

**文档版本：** 1.3 (结构完整、新增文本及占位符版本)
**基于状态：** 迭代一核心功能完成，后端云端部署及API Client重构完成。(截至 2025年5月13日)
**核心贡献者：** Alec, ADC v1.6
**目标读者：** AI开发协调员 (ADC), 技术开发者

---

## 1. 引言与文档目的

本文档旨在为“AI学习陪伴系统”项目提供一份详尽的技术参考和问题排查指南。它深入介绍了项目的技术架构、代码结构、核心模块实现细节、云端部署配置，以及在开发、部署和运行过程中可能遇到的常见问题及其定位和解决策略。

本文档的目标是帮助技术参与者（特别是新任ADC）快速理解系统的技术实现和云端部署状态，能够有效地进行后续开发、维护和问题排查。它整合了截至云端部署初步完成后的最新技术状态和调试经验。

**文档版本管理：** 本文档将与项目核心代码一同在项目的Git仓库中进行版本控制和管理。所有重要的修订都将反映在文档顶部的“文档版本”号上，并建议在提交相关代码变更时，同步更新受影响的文档部分。我们致力于维护本文档的准确性和时效性，使其成为项目可靠的技术参考。

---

## 2. 技术架构与选型概览

[编者注：此章节的详细原始描述请参考或合并自项目v1.1版本的对应内容，并与以下v1.3版本中针对特定子项的补充/修订（如API路由前缀、关键技术栈版本）进行整合。]

本项目旨在构建一个AI辅助的学习工具，核心功能是处理用户提供的学习材料（B站视频链接或文本转录稿），通过AI技术栈（ASR、LLM）生成学习笔记、知识点提示等，并提供云端访问能力。

### 2.1. 后端 (Backend)
* **框架:** Python 3.12, FastAPI
    * FastAPI以其高性能和易用性被选为构建API服务的基础框架。它内置了基于Pydantic的数据校验和基于Starlette的异步能力。
* **API 路由前缀 (API Route Prefix):** 为确保API版本管理和路径的清晰性，所有后端API端点均统一以 `/api/v1/` 作为路径前缀。例如，一个用于创建学习会话的端点，其从根路径开始的完整路径应为 `/api/v1/learning_sessions/`。前端应用在发起请求时（通过 `frontend_web/src/services/apiClient.js` 模块）会自动处理此前缀的添加。
* **ORM & 数据校验:** SQLAlchemy (Core + ORM), Pydantic
    * SQLAlchemy用于与数据库进行交互，实现数据持久化。
    * Pydantic模型用于API请求/响应的数据校验、序列化以及应用内部配置管理（`app/core/config.py`）。
* **数据库:** OceanBase Cloud (MySQL 兼容模式)
    * 通过标准的 `mysql-connector-python` 驱动进行访问。
    * 连接配置通过环境变量 `DATABASE_URL` 管理。
* **数据库连接池:** SQLAlchemy Engine 配置
    * 当前使用 `create_engine` 的默认连接池配置。为增强生产环境稳定性，在 `app/db/database.py` 中为 `create_engine` 函数已考虑添加参数如 `pool_pre_ping=True` (在每个连接被检出前执行一个简单的查询以测试其活性) 和 `pool_recycle=1800` (例如，每30分钟回收一次连接，防止因数据库或网络策略导致的连接失效)。
* **异步处理:** FastAPI 原生支持 `async/await`。
    * 对于CPU密集型或同步IO阻塞型任务（如调用外部`yt-dlp`、`ffmpeg`，或某些同步的AI SDK调用），会使用 `asyncio.to_thread` 或 FastAPI的 `BackgroundTasks` 来避免阻塞主事件循环。
* **部署平台:** Render (通过 Docker 部署)。
    * *[编者注：原v1.1文档中关于此部分的其他细节应予保留和整合。]*

### 2.2. 前端 (Frontend)
* **框架/库:** React (v19+), Vite (构建工具)
* **核心依赖:** `react-markdown`, `remark-gfm`
* **API客户端:** 使用自定义的 `frontend_web/src/services/apiClient.js` 模块统一处理对后端API的调用（详见3.3.1节）。
* **部署平台:** Vercel。
    * *[编者注：原v1.1文档中关于此部分的其他细节应予保留和整合。]*

### 2.3. AI模型与核心外部工具
* **语音转写 (ASR):** 讯飞语音识别大模型 (长音频转写服务)。
* **笔记与知识点生成:** Google Gemini 1.5 Flash。
* **视频下载工具:** `yt-dlp`。
* **音视频处理工具:** `ffmpeg`。
    * *[编者注：原v1.1文档中关于此部分对各工具用途的详细描述应予保留和整合。]*

### 2.4. 配置管理
* **后端 (Render):** 通过 Render 平台的环境变量设置，由 `app/core/config.py` 读取。
* **前端 (Vercel):** 通过 Vercel 平台的环境变量设置（核心为 `VITE_API_BASE_URL`）。
    * *[编者注：原v1.1文档中关于此部分的更详细描述应予保留和整合。]*

#### 2.5. 关键技术栈版本参考 (Key Technology Stack Versions) (新增内容)
为确保开发、部署环境的一致性并辅助问题排查，以下列出项目在本文档版本（1.3）发布时所依赖的核心技术栈及其主要版本号。请注意，最准确的版本信息应始终以项目根目录下的配置文件（如 `requirements.txt` 用于后端Python依赖, `frontend_web/package.json` 用于前端Node.js依赖）为准。

* Python: ~3.12.x
* FastAPI: [请从 `requirements.txt` 查阅并填入，例如 ~0.109.2]
* SQLAlchemy: [请从 `requirements.txt` 查阅并填入，例如 ~2.0.25]
* Pydantic: [请从 `requirements.txt` 查阅并填入，例如 ~2.5.3]
* React: ~19 (Beta) (或由 `package.json` 决定)
* Vite: [请从 `package.json` 查阅并填入，例如 ~5.1.0]
* Node.js (Vercel构建环境及本地开发推荐): ~20.x LTS
* OceanBase Cloud (兼容模式): MySQL 5.7 / 8.0 兼容
* `yt-dlp`: [建议记录安装时版本或要求使用较新版本，例如 ~2023.12.30]
* `ffmpeg`: [建议记录`Dockerfile`中安装的版本或来源，例如 ~6.0]

---

## 3. 项目文件结构详解

[编者注：此章节的详细原始描述（介绍根目录下的`Dockerfile`, `app/`, `frontend_web/`, `scripts/`, `.env`, `requirements.txt`, `.gitignore`等）请参考或合并自项目v1.1版本的对应内容。以下为v1.3版本新增的子章节，或对原有子章节的重点提示。]

### 3.1. 项目根目录及核心文件
    * *[编者注：原v1.1文档中关于此部分的详细描述应予保留。]*

### 3.2. 后端结构详解 (`app/`)
    * *[编者注：原v1.1文档中关于`app/main.py`, `app/core/config.py`, `app/db/database.py`, `app/db/models.py`等关键文件在云部署适配中的变更细节（如`DATABASE_URL`的统一使用，`LONGTEXT`类型，`created_at`字段等）应予保留和整合。]*

### 3.3. 前端核心服务模块 (`frontend_web/src/services/`) (新增子章节)

#### 3.3.1. API 客户端 (`apiClient.js`) (新增内容)
为实现前端对后端API调用的统一管理、提升代码的可维护性、标准化请求行为并集中处理通用逻辑（如URL构建、错误处理），项目中在 `frontend_web/src/services/apiClient.js` 路径下引入了中央API客户端模块。

**核心职责与设计原则：**
* **统一API调用出口：** 所有从前端（React组件）发往后端FastAPI服务的HTTP请求，都应通过此模块中导出的函数进行。
* **集中的URL与路径管理：**
    * 模块内部通过 `const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;` 获取在Vercel等部署平台配置的基础URL。
    * 模块内部定义并统一应用API版本前缀 `const API_PREFIX = '/api/v1';` 到所有请求路径中。
    * 组件层面在调用API时，无需关心这些基础URL和前缀的拼接细节。
* **通用的请求处理函数 (`request`)：**
    * 模块内部实现了一个私有的（未导出） `async function request(endpoint, options = {})` 基础函数，作为所有具体API请求的底层实际执行者。
    * 此 `request` 函数负责：安全构造完整URL（处理 `API_BASE_URL` 可能的末尾斜杠，确保 `endpoint` 以 `/` 开头，检查 `API_BASE_URL` 是否已定义）、设置标准HTTP请求头（`'Content-Type': 'application/json'`, `'Accept': 'application/json'`）并允许合并自定义头、根据HTTP方法和传入的`body`（如果存在）正确处理请求体（`JSON.stringify`，并对不应有body的请求方法给出警告）、执行底层的 `Workspace` API调用、对响应进行统一处理（检查 `response.ok` 状态，处理204 No Content等特殊情况，基于`Content-Type`头部尝试解析JSON响应数据，对JSON解析失败进行细致的错误处理）、以及实现标准化的错误对象构造与抛出（错误对象包含`status`, `statusText`, 和从响应体解析的错误数据`data`等属性）。
* **具名化的API函数导出：**
    * 针对项目中每一个具体的后端API端点，`apiClient.js` 模块都会定义并 **导出** 一个对应的、具名化的异步函数，例如：
        * `export async function createLearningSession(data)`
        * `export async function getLearningSessionStatus(sessionId)`
        * `export async function getLearningSessionNotes(sessionId)`
        * `export async function getLearningSessionKnowledgeCues(noteId)`
    * 这些导出的函数内部会调用通用的 `request` 函数，并传入该API端点特定的路径、HTTP方法以及必要的参数，同时通常会包含对输入参数的校验。

**使用方式示例：**
* 在React组件中，首先从 `apiClient.js` 导入所需的API函数：
    ```javascript
    import { createLearningSession } from '../services/apiClient'; // 路径根据组件位置调整
    ```
* 然后在组件的业务逻辑中异步调用这些函数：
    ```javascript
    try {
      const payload = { source_type: 'url', source_content: 'some_url' };
      const responseData = await createLearningSession(payload);
      // 处理成功的响应 responseData
    } catch (error) {
      // error 对象通常包含 status, message, 和 data (其中可能包含 detail) 等属性
      console.error('API call failed:', error.message, error.data ? error.data.detail : '');
      // 向用户显示更友好的错误信息
    }
    ```

**引入API Client的主要优点：**
* **简化组件逻辑：** React组件的代码将更加专注于UI渲染和应用状态管理。
* **提高代码的可维护性：** API相关的变更只需在`apiClient.js`一处修改。
* **增强代码的一致性和健壮性：** 所有API调用都遵循统一模式。

---

## 4. 云端部署配置详解

[编者注：此章节的详细原始描述请参考或合并自项目v1.1版本的对应内容，并与以下v1.3版本中针对特定子项的修订进行整合。]

### 4.1. 后端部署 (Render)
    * *[编者注：原v1.1文档中关于Render部署方式、`Dockerfile`关键内容、Render服务配置（实例类型、环境变量如`DATABASE_URL`, `GOOGLE_API_KEY`等格式与示例、Auto-Deploy）的详细描述应予保留。]*

### 4.2. 前端部署 (Vercel)
    * *[编者注：原v1.1文档中关于Vercel部署方式、项目配置（框架预设、根目录`frontend_web`、构建命令、输出目录）的详细描述应予保留。以下为对环境变量部分的修订。]*
#### Environment Variables (关键)
* `VITE_API_BASE_URL`: 指向部署在 Render 上的后端服务的**根URL (Root URL)**，例如 `https://your-render-app-name.onrender.com`。
    * **重要说明：** 此URL本身**不应包含**任何路径部分（如 `/api/v1/`）或末尾的斜杠 (`/`)。所有API的路径前缀（即 `/api/v1/`）和具体的端点路径（如 `/learning_sessions/`）都将在前端的中央API客户端模块 (`frontend_web/src/services/apiClient.js`) 中进行统一、规范的拼接和管理。
* *[编者注：原v1.1文档中关于此部分其他Vercel环境变量的描述应予保留。]*

### 4.3. 数据库配置 (OceanBase Cloud)
    * *[编者注：原v1.1文档中关于OceanBase Cloud网络访问控制（白名单 `ob_tcp_invited_nodes`）、SSL/TLS注意事项、用户权限等详细描述应予保留。]*

---
## 5. 核心数据流概要 (云端部署后)
[编者注：此章节的详细原始描述请参考或合并自项目v1.1版本的对应内容。v1.3版本的一个关键变化是，前端发起的API请求现在统一通过`apiClient.js`模块进行，这可能需要对原数据流描述中关于前端API调用部分的文字进行微调，以反映这一变化。]

---

## 6. 通用问题排查策略 (云端部署后总结)
[编者注：此章节的详细原始描述（如从日志入手、明确问题范围、检查配置、验证外部服务连通性、代码与环境一致性、逐步调试简化、数据库模式同步问题、Render特定退出码问题等通用策略）请参考或合并自项目v1.1版本的对应内容。以下为v1.3版本新增或强化的子点。]

**X. 诊断前端发起的API调用失败（尤其是 404 Not Found 错误）：** (新增或强化此子点)
当在浏览器开发者工具的"Network"页签中观察到前端向后端发起的API请求返回404（Not Found）状态码时，这通常表示服务器无法找到请求的特定URL资源。请按以下步骤系统排查：
1.  **核对前端环境变量 `VITE_API_BASE_URL` (在Vercel中配置)：**
    * **准确性：** 登录Vercel平台，检查项目中配置的 `VITE_API_BASE_URL` 环境变量的值是否准确无误，它应指向您部署在Render上的后端服务的**根URL**（例如 `https://your-render-app-name.onrender.com`）。
    * **格式：** 确认此URL**不包含**任何路径部分（如 `/api/v1/`）或末尾的斜杠 (`/`)。
2.  **检查前端代码中URL的构建逻辑 (主要在 `frontend_web/src/services/apiClient.js` 中)：**
    * **API前缀 (`API_PREFIX`)：** 确认 `apiClient.js` 中定义的 `API_PREFIX` 常量是否正确（目前应为 `/api/v1/`），并且是否被稳定、正确地添加到了所有请求的基础URL之后、具体端点路径之前。
    * **端点路径 (Endpoint Path)：** 对于发起调用的具体函数（如 `createLearningSession`, `getLearningSessionStatus` 等），检查其内部构造的 `endpoint` 字符串（例如 `/learning_sessions/` 或 `/learning_sessions/${sessionId}/status`）是否与后端FastAPI应用中定义的实际路由路径完全一致。特别注意路径参数的格式、是否有遗漏或多余的斜杠。
    * **完整URL审查：** 在浏览器开发者工具的Network标签页中，找到失败的请求，仔细查看其"Request URL"字段。将这个完整的URL与您期望的正确URL（`API_BASE_URL` + `API_PREFIX` + `endpoint`）进行比对，查找任何可能的拼接错误、字符遗漏或多余字符。
3.  **核对HTTP方法 (Method)：**
    * 确认前端代码（在 `apiClient.js` 的 `request` 函数调用中）为该API请求指定的HTTP方法（例如GET, POST等）与后端API路由定义中允许的方法是否匹配。
4.  **检查后端服务 (Render) 状态与应用日志：**
    * **服务运行状态：** 登录您的Render控制台，确认目标后端服务是否处于正常的"Live"或"Healthy"状态。
    * **应用运行时日志：** 仔细查阅Render后端服务的"Logs"页签。如果请求已到达FastAPI应用层面但因路由未匹配而返回404，Uvicorn/FastAPI通常会在日志中记录相关信息。如果完全没有对应请求的日志，问题可能出在更早阶段。
5.  **后端路由定义最终确认 (代码层面)：**
    * 回到后端FastAPI项目的源代码中，再次仔细核对相关API路由的定义，确保目标路径、HTTP方法等均已按预期正确定义并部署。

#### 6.1. 日志与监控策略（概览与展望） (新增子章节或整合入原日志相关内容)
**当前实践：**
* **后端 (Render/FastAPI)：** Render平台标准日志输出，Uvicorn日志级别`debug`，代码内`print()`及`traceback`。
* **前端 (Vercel/React)：** 浏览器开发者工具Console。
* **数据库 (OceanBase Cloud)：** 平台自带监控与日志工具。

**未来展望与可考虑的增强方向：**
* **结构化日志：** 后端（如`Loguru`或`logging`），前端（轻量级库）。
* **日志聚合与分析：** 集中管理平台（如Sentry, Datadog等）。
* **应用性能监控 (APM)：** （如Sentry Performance, Datadog APM等）。
* **自定义业务指标监控与告警。**

---
## V. 本地开发环境搭建指南 (Local Development Setup Guide) (新增章节 - 详细步骤)

本章节旨在为新开发者或需要在新机器上设置项目的开发者，提供一个清晰、完整的在本地计算机上搭建和运行"AI学习陪伴系统"全套开发环境的步骤指引。

**V.1 前提条件 (Prerequisites)**
* **Git 客户端：** 用于版本控制和代码下载。从 [https://git-scm.com/](https://git-scm.com/) 下载并安装。
* **Python：** 版本需符合 "2.5. 关键技术栈版本参考" 章节中的指定（例如 ~3.12.x）。建议通过 `pyenv` 或直接从 [https://www.python.org/](https://www.python.org/) 安装。确保 `pip` 和 `venv` 可用。
* **Node.js：** 版本需符合 "2.5. 关键技术栈版本参考" 章节中的指定（例如 ~20.x LTS）。建议通过 `nvm` 或直接从 [https://nodejs.org/](https://nodejs.org/) 安装。确保 `npm` (或 `yarn`，如果项目统一使用) 可用。
* **Docker Desktop (推荐)：** 虽然不是绝对必须（如果已有其他方式管理本地数据库），但推荐安装 Docker Desktop ([https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/))。它可以方便地用于本地运行与OceanBase Cloud兼容的MySQL实例（或其他数据库），以及未来可能需要的其他服务容器。
* **代码编辑器：** 推荐 Visual Studio Code (VS Code) 或其他您熟悉的IDE。

**V.2 获取代码 (Getting the Code)**
1.  打开您的终端或命令行工具。
2.  导航到您希望存放项目的本地目录。
3.  执行 `git clone <项目Git仓库的URL>` 命令克隆项目代码库。
4.  执行 `cd ai_learning_companion_mvp` (或您的项目根目录名) 进入项目。

**V.3 后端 (`app/`) 配置与启动**
1.  **创建并激活Python虚拟环境：**
    * 在项目根目录下，执行： `python -m venv .venv` (或 `python3 -m venv .venv`)
    * 激活虚拟环境：(macOS/Linux: `source .venv/bin/activate`; Windows: `.venv\Scripts\activate`)
2.  **安装Python依赖：** `pip install -r requirements.txt`
3.  **配置后端环境变量 (`.env` 文件)：**
    * 在项目**根目录**下（与 `app/` 和 `frontend_web/` 同级），创建一个名为 `.env` 的文件。
    * 您可以复制 `.env.example` (如果项目中提供了此模板文件) 并重命名为 `.env`。
    * 编辑 `.env` 文件，至少需要配置以下变量：
        * `DATABASE_URL`: 指向您的本地测试数据库。
            * **推荐使用Docker运行本地MySQL实例（兼容OceanBase）：**
                * 如果您安装了Docker Desktop，可以在项目根目录创建一个简单的 `docker-compose.yml` 文件（如果项目未提供）来启动一个MySQL服务，例如：
                  ```yaml
                  # docker-compose.yml (示例)
                  version: '3.8'
                  services:
                    db_mysql_local:
                      image: mysql:8.0 
                      ports:
                        - "3307:3306" # 将容器的3306端口映射到主机的3307端口 (避免与本地已安装的MySQL冲突)
                      environment:
                        MYSQL_ROOT_PASSWORD: your_strong_password
                        MYSQL_DATABASE: ai_learning_companion_db_local # 建议本地数据库名与云端有所区别
                        MYSQL_USER: alec_local
                        MYSQL_PASSWORD: local_password
                      volumes:
                        - mysql_data_local:/var/lib/mysql 
                  volumes:
                    mysql_data_local:
                  ```
                * 然后在终端运行 `docker-compose up -d` (或 `docker compose up -d`)。
                * 此时，您的 `DATABASE_URL` 可以设置为：`mysql+mysqlconnector://alec_local:local_password@localhost:3307/ai_learning_companion_db_local` (注意端口号)。
            * 或者，如果您有其他本地MySQL服务或云端测试数据库，请相应配置连接字符串。
        * `GOOGLE_API_KEY`: 您的Google Gemini API密钥。
        * `XUNFEI_APPID`: 您的讯飞 App ID。
        * `XUNFEI_API_SECRET`: [请根据讯飞SDK实际需要的环境变量名填写，例如讯飞通常需要APISecret和APIKey]
        * `XUNFEI_API_KEY`: [请根据讯飞SDK实际需要的环境变量名填写]
    * **重要：** 确保 `.env` 文件已被添加到 `.gitignore` 中，以防意外提交敏感信息。
4.  **数据库初始化/迁移：**
    * **当前项目启动时自动建表：** 后端应用 (`app/main.py`) 的启动事件中包含了 `create_db_tables()` 函数，它会使用SQLAlchemy的 `Base.metadata.create_all(bind=engine)` 来自动创建在 `app/db/models.py` 中定义的表（如果它们尚不存在）。对于初次本地设置，这通常足够。
    * **[占位符：如果未来引入数据库迁移工具（如Alembic）：** 此处应补充执行数据库迁移命令的步骤（例如 `alembic upgrade head`），以确保数据库模式与最新的模型定义一致。]
5.  **启动后端开发服务器：**
    * 确保您的Python虚拟环境已激活，并且您位于项目根目录。
    * 执行：`python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
    * `--host 0.0.0.0` 使服务可以从本地网络访问。
    * `--port 8000` 指定服务运行端口（可修改，但需与前端配置对应）。
    * `--reload` 会在代码变更时自动重启服务器，便于开发。
    * 您应该能看到Uvicorn启动日志，表明FastAPI应用正在运行。

**V.4 前端 (`frontend_web/`) 配置与启动**
1.  **进入前端目录：** 打开一个新的终端窗口/标签页，从项目根目录执行 `cd frontend_web`。
2.  **安装Node.js依赖：**
    * 执行：`npm install` (或者，如果项目统一使用yarn，则执行 `yarn install`)。
3.  **配置前端环境变量：**
    * 在 `frontend_web/` 目录下，依据 `.env.example` (如果项目提供了此模板文件) 创建一个 `.env.local` 文件 (Vite推荐用于本地覆盖，且默认被gitignore)。如果仅使用 `.env`，请确保它也被gitignore。
    * 编辑该env文件，核心配置是 `VITE_API_BASE_URL`。将其值设置为您本地运行的后端服务的地址，例如：
        `VITE_API_BASE_URL=http://localhost:8000`
        * **注意：** 此URL应与您后端Uvicorn服务器启动时使用的端口号一致，并且**不应包含** `/api/v1` 前缀。
4.  **启动前端开发服务器：**
    * 执行：`npm run dev` (或 `yarn dev`)。
    * Vite会启动开发服务器，并在终端输出前端应用的访问地址（通常是 `http://localhost:5173` 或类似端口）。

**V.5 验证本地环境联通**
1.  在浏览器中打开Vite开发服务器提供的URL (例如 `http://localhost:5173`)。
2.  尝试使用应用的核心功能，例如提交一段文本或一个B站链接。
3.  **观察：**
    * 浏览器开发者工具的"Network"页签，看前端是否向 `http://localhost:8000/api/v1/...` 发起了请求，以及请求是否成功。
    * 后端Uvicorn服务器的终端日志，看是否有API请求的记录和处理信息。
    * 前端浏览器的Console，看是否有JavaScript错误。
4.  如果一切正常，您应该能够完成一次完整的处理流程并在前端看到结果。

---
## W. 安全注意事项 (Security Considerations) (新增章节)

在确保功能实现的同时，项目的安全性也至关重要。除已在特定章节（如数据库白名单、SSL/TLS连接）中提及的安全措施外，还应普遍关注以下方面：
* **API密钥与敏感配置管理：** 必须通过环境变量配置，严禁硬编码或入库。后端通过 `app/core/config.py` 读取。
* **依赖库安全：** 定期审查依赖（`requirements.txt`, `package.json`）并更新已知漏洞。使用 `pip audit` / `npm audit`。
* **FastAPI应用安全：** 利用Pydantic进行输入校验。合理配置CORS。HTTPS由部署平台处理。
* **云平台安全配置：** 遵循Render/Vercel最佳实践，管理权限，监控行为。
* **输入数据处理：** 对用户输入（URL、文本等）保持警惕，进行适当校验清理以防恶意输入。

---
## X. 核心架构图示 (Conceptual Architecture Diagrams) (新增章节 - 详细文字描述)

为了更直观地理解系统组件及其交互，以下提供了对关键架构图示的文字描述。未来迭代中，这些描述可用于生成实际的图表（例如使用Mermaid.js）。

### X.1 系统上下文图 (System Context Diagram) - 文字描述
* **中心系统：** "AI学习陪伴系统"。
* **主要用户角色：** "学习者 (Learner)"。通过前端Web界面与系统交互。
* **外部系统依赖与交互：**
    * **内容源 (如Bilibili):** 用户提供URL，系统后端通过 `yt-dlp` 下载。
    * **讯飞语音API (Xunfei ASR API):** 后端发送音频进行语音转文字。
    * **Google Gemini API (LLM):** 后端发送文本进行预处理、笔记生成、知识点提示生成。
* **核心数据流：** 用户通过前端提交 -> 前端调后端API (通过`apiClient.js`) -> 后端编排服务与外部系统交互，结果存入数据库 -> 前端轮询状态(通过`apiClient.js`)并展示。

### X.2 容器图 (Container Diagram - Key Services) - 文字描述
* **前端应用容器 (Frontend Application @ Vercel):** React SPA (Vite构建)。负责UI和用户交互。通过HTTPS与后端API服务通信。
* **后端API服务容器 (Backend API Service @ Render Docker):** Python, FastAPI, Uvicorn。负责API接口、业务编排、与DB及外部AI服务交互。通过HTTPS暴露API。
* **数据库服务 (Database @ OceanBase Cloud):** OceanBase Cloud (MySQL兼容)。持久化核心数据。后端通过SSL/TLS的MySQL协议连接。
* **外部AI服务 (External AI Services - 作为外部依赖，非本项目容器):** 讯飞ASR API (HTTPS), Google Gemini API (HTTPS)。
* **主要技术通信路径：**
    * 用户浏览器 <-> 前端应用 (Vercel): HTTPS
    * 前端应用 (Vercel) <-> 后端API服务 (Render): HTTPS (调用 `/api/v1/...` 端点，由`apiClient.js`封装)
    * 后端API服务 (Render) <-> 数据库 (OceanBase Cloud): TCP/IP over SSL/TLS (MySQL协议)
    * 后端API服务 (Render) <-> 讯飞ASR API: HTTPS
    * 后端API服务 (Render) <-> Google Gemini API: HTTPS
    * 后端API服务 (Render) -> `yt-dlp`/`ffmpeg` (作为本地子进程或库调用)

---
## Y. 核心数据模型 (Conceptual Data Model) (新增章节 - 实体与初步属性描述)

本章节旨在提供一个关于项目核心数据实体及其相互关系的高层概念视图。详细数据库表定义见 `app/db/models.py`。

### Y.1 主要数据实体及其核心属性
* **`LearningSession` (学习会话):**
    * `session_id` (UUID, 主键): 会话唯一标识。
    * `status` (String): 当前会话的处理状态 (枚举值，例如: `processing_initiated`, `video_download_pending`, `video_downloading`, `video_downloaded`, `audio_extraction_pending`, `audio_extraction_completed`, `asr_pending`, `asr_completed`, `notes_generation_pending`, `notes_generated`, `cues_generation_pending`, `all_processing_complete`, `error_in_processing`, `error_in_asr`, `error_in_llm_module_a1`, `error_in_llm_module_b` 等)。
    * `error_message` (Text, 可空): 如果处理出错，记录详细错误信息或堆栈。
    * `created_at` (DateTime): 会话创建时间 (自动生成，带默认值)。
    * `updated_at` (DateTime): 会话最后更新时间 (自动更新)。
    * `source_id` (ForeignKey -> LearningSource, 可空): 关联的学习源ID。
    * `user_id` (String/UUID, 可空，未来扩展): 关联的用户ID。

* **`LearningSource` (学习源):**
    * `source_id` (UUID, 主键): 学习源唯一标识。
    * `source_type` (String, 必填): 来源类型 (枚举值: `'url'`, `'text'`)。
    * `source_content` (Text, 必填): 来源的具体内容（B站视频URL，或用户提交的完整文本）。
    * `initial_video_title` (String, 可空): 用户提交时提供的初始视频标题（如果是URL类型）。
    * `initial_source_description` (Text, 可空): 用户提交时提供的初始来源描述。
    * `downloaded_video_filename` (String, 可空): 如果是URL类型，视频下载到服务器后的文件名或标识。
    * `extracted_audio_filename` (String, 可空): 从视频中提取出的音频文件名或标识。
    * `raw_transcript_text_id` (String/ForeignKey, 可空): 指向存储完整原始转录文本的位置（例如，如果文本过大，可能存入对象存储或特定大文本字段）。（或者直接使用 `LONGTEXT` 如下）
    * `raw_transcript_text` (LONGTEXT, 可空): ASR服务返回的原始完整转录文本，或用户直接输入的文本（如果无时间戳）。
    * `structured_transcript_segments_json` (JSON/LONGTEXT, 可空): 包含时间戳和分段文本的结构化转录稿（例如，从ASR结果解析得到，或用户输入时自带的结构）。
    * `ai_generated_title` (String, 可空): AI（例如模块A.1或专门的标题生成模块）为学习内容生成的优化后标题。
    * `processing_metadata_json` (JSON, 可空): 存储处理过程中的其他元数据（例如，视频时长、ASR耗时等）。
    * `created_at` (DateTime): 记录创建时间。

* **`GeneratedNote` (AI生成的学习笔记):**
    * `note_id` (UUID, 主键): 笔记唯一标识。
    * `session_id` (ForeignKey -> LearningSession, 必填): 关联的会话ID。
    * `markdown_content` (LONGTEXT, 必填): Markdown格式的笔记内容。
    * `summary_of_note` (Text, 可空): AI（模块B）生成的笔记摘要。
    * `key_concepts_mentioned` (JSON/Text, 可空): AI（模块B）识别的笔记中提及的核心概念列表（例如字符串数组）。
    * `estimated_reading_time_seconds` (Integer, 可空): AI（模块B）估算的笔记阅读时长（秒）。
    * `llm_module_version_info_json` (JSON, 可空): 生成此笔记的LLM模块（如模块B）及其Prompt版本等信息。
    * `created_at` (DateTime): 记录创建时间。

* **`KnowledgeCue` (AI生成的知识点提示):**
    * `cue_id` (UUID, 主键): 知识点提示唯一标识。
    * `note_id` (ForeignKey -> GeneratedNote, 必填): 关联的笔记ID。
    * `question_text` (Text, 必填): 提示的问题文本。
    * `answer_text` (Text, 必填): 提示的答案文本。
    * `difficulty_level` (String, 可空): 知识点难度级别 (例如: 'Low', 'Medium', 'High')。
    * `source_reference_in_note` (String, 可空): 该知识点在笔记中的参考位置或相关章节/段落标识。
    * `llm_module_version_info_json` (JSON, 可空): 生成此知识点的LLM模块及其Prompt版本等信息。
    * `created_at` (DateTime): 记录创建时间。

### Y.2 实体间主要关系
* 一个 `LearningSession` 通常精确关联一个 `LearningSource` (一对一关系)。
* 一个 `LearningSession` 通常期望产生一个核心的 `GeneratedNote` (目前设计为一对一关系)。
* 一个 `GeneratedNote` 可以关联多个 `KnowledgeCue` (一对多关系)。

*(这是一个初步的、概念性的数据模型描述，旨在辅助理解。实际的数据库模式由 `app/db/models.py` 中的SQLAlchemy模型精确定义，并可能随着项目迭代而演进。)*

---
## Z. 架构原则与设计理念 (Guiding Architectural Principles) (新增章节)

本项目在技术选型、代码实现和系统设计过程中，将参考并努力遵循以下原则，以保障系统的可维护性、可扩展性和长期健康发展：
* **模块化与单一职责 (Modularity and Single Responsibility):**
    * AI模块应尽可能"一个AI（及其Prompt）专注于一个核心任务"，以提升其专业性和输出质量，并便于独立优化和迭代。
    * 前端组件和服务（如 `apiClient.js`）也应追求高内聚、低耦合，每个模块有清晰的职责边界。
* **配置优于硬编码 (Configuration over Hardcoding):**
    * 对于可能变化的参数、URL、API密钥、功能开关等，优先使用环境变量（通过 `.env` 文件本地管理，通过云平台注入生产环境）或配置文件进行管理，避免在代码中硬编码。
* **API客户端模式 (API Client Pattern):**
    * 前端通过中央API客户端 (`frontend_web/src/services/apiClient.js`) 与后端交互，以统一管理API路径构造、请求头、错误处理等通用逻辑，简化组件代码并增强可维护性。
* **代码清晰与可读性 (Clarity and Readability):**
    * 努力编写易于人类开发者（以及未来的AI）理解和维护的代码。
    * 辅以必要的、有意义的注释（例如JSDoc风格的函数注释）和本文档这样的外部文档。
* **迭代与演进 (Iteration and Evolution):**
    * 接受架构和设计是逐步演进的。在项目早期，可能为了快速交付核心价值而采取一些简化方案。
    * 随着项目的深入和对需求的理解加深，应定期回顾技术选型和架构设计，并进行必要的重构和优化（例如本次API Client的引入），以适应新的需求和提升系统质量。
* **用户中心 (User-Centric):**
    * 所有技术决策和功能设计最终都应服务于提升用户体验和解决用户实际问题。
* **[占位符：未来根据项目实践和决策，持续补充其他重要原则，例如关于自动化测试的覆盖要求、API设计规范、数据一致性保障策略、安全性设计原则、错误处理与恢复策略等方面的具体条目。]**