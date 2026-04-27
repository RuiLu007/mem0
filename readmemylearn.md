# Mem0 项目学习笔记

## 项目介绍

> **一句话理解：** Mem0 是一个给 AI 助手/AI Agent 增加“长期记忆”的项目。

它解决的核心问题是：  
大模型本身没有真正的长期记忆，用户偏好、历史事实、上下文状态很容易丢失。Mem0 通过 **记忆提取 + 向量存储 + 检索召回 + 多种 LLM/Embedding/向量库适配**，让 AI 应用可以“记住用户”。

这个仓库不是单一 Python 服务，而是一个 **多模块 monorepo**。如果只看 Python 部分，重点有 3 块：

1. `mem0/`：核心 Python SDK，真正的记忆能力都在这里。
2. `openmemory/api/`：适合本地学习和调试的 FastAPI 服务。
3. `server/`：更偏部署型的 Mem0 REST API 服务，依赖更重。

### 真正的启动入口文件

如果你是为了 **本地学习、调试、跑通 Python 服务**：

- **推荐主入口：`openmemory/api/main.py`**

如果你是为了 **启动独立的 Mem0 REST API 服务**：

- **服务入口：`server/main.py`**

> **重点：** 根目录下的 `mem0/` 不是 Web 服务入口，它是 SDK 包源码。

## 推荐启动方式（uv）

### 1. 最推荐的本地学习入口：`openmemory/api/main.py`

这个入口最适合新手，因为：

- 默认数据库就是 **SQLite**
- 首次导入时会自动建表
- 用 `uv` 就能直接跑起来
- 我已经按这条链路验证过：`from main import app` 可以正常导入

### 2. 完整启动步骤（100% 适配 uv）

```bash
cd openmemory/api

# 1）创建虚拟环境
uv venv .venv

# 2）激活环境
source .venv/bin/activate

# 3）安装当前服务依赖
uv pip install -r requirements.txt

# 4）把仓库根目录的 mem0 SDK 以可编辑模式装进当前环境
uv pip install -e ../..

# 5）复制环境变量文件
cp .env.example .env
```

然后编辑 `openmemory/api/.env`：

```env
OPENAI_API_KEY=你的_OPENAI_KEY
USER=你的用户ID
```

### 3. 数据库初始化

这个服务默认使用：

- **SQLite 文件：`openmemory/api/openmemory.db`**

而且数据库初始化逻辑写在 `openmemory/api/main.py` 中：

- `Base.metadata.create_all(bind=engine)`：自动建表
- `create_default_user()`：自动创建默认用户
- `create_default_app()`：自动创建默认应用

所以首次初始化直接执行：

```bash
uv run --active python -c "from main import app; print(app.title)"
```

看到输出 `OpenMemory API` 就说明：

- 依赖已安装
- 环境变量已加载
- SQLite 已初始化
- FastAPI 应用已成功导入

### 4. 启动服务

```bash
uv run --active uvicorn main:app --host 0.0.0.0 --port 8765 --reload
```

启动后访问：

- Swagger 文档：`http://127.0.0.1:8765/docs`
- ReDoc：`http://127.0.0.1:8765/redoc`

---

### 5. `server/main.py` 的启动说明

`server/main.py` 也是 Python 入口，但它不是最轻量的本地学习入口。

它默认依赖：

- PostgreSQL + pgvector
- OpenAI API Key
- `psycopg` 的二进制运行时支持

如果你要跑它，建议步骤如下：

```bash
cd server

uv venv .venv
source .venv/bin/activate

uv pip install -r requirements.txt
uv pip install -e ..
uv pip install "psycopg[binary]>=3.2.8" "psycopg-pool>=3.2.6,<4.0.0"

cp .env.example .env
```

`.env` 至少要配置：

```env
OPENAI_API_KEY=你的_OPENAI_KEY
POSTGRES_HOST=你的PostgreSQL地址
POSTGRES_PORT=5432
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_COLLECTION_NAME=memories
ADMIN_API_KEY=你自己的管理密钥
```

启动命令：

```bash
uv run --active uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

> **注意：** 这个服务不是“纯 Python 零依赖本地启动”，数据库必须先准备好；因此学习阶段优先跑 `openmemory/api/main.py`。

## 架构设计

## 1. 仓库层级结构

这个仓库可以理解成 3 层：

| 层级 | 目录 | 作用 |
| --- | --- | --- |
| 核心能力层 | `mem0/` | 记忆抽取、存储、检索、客户端、Provider 工厂 |
| 服务封装层 | `openmemory/api/`、`server/` | 把核心能力包装成 API 服务 |
| 配套生态层 | `cli/`、`docs/`、`examples/`、`tests/` | 命令行、文档、示例、测试 |

## 2. Python 核心调用链

最核心的执行链路可以理解为：

```text
FastAPI / Client 请求
        ↓
Memory / MemoryClient
        ↓
配置解析（configs）
        ↓
Factory 工厂选择 provider
        ↓
LLM / Embedding / Vector Store / Reranker
        ↓
完成 memory add / search / get / update / delete
```

## 3. `openmemory/api` 的服务流程

### 写入记忆

```text
HTTP 请求
→ router 处理请求
→ 校验用户 / app
→ get_memory_client()
→ Memory.add(...)
→ 写入向量库
→ 同步写入本地 SQLAlchemy 数据库
→ 返回结果
```

### 搜索记忆

```text
HTTP 请求
→ router
→ memory client
→ embedding query
→ vector_store.search(...)
→ 权限过滤
→ 返回命中的 memory
```

## 核心功能

### 1. 记忆写入

入口主要在：

- `mem0/memory/main.py`
- `openmemory/api/app/routers/memories.py`
- `server/main.py`

作用：

- 接收对话消息或文本
- 调用 LLM 抽取可长期保存的事实
- 组织 metadata / filters
- 写入向量数据库

### 2. 记忆检索

核心能力在：

- `Memory.search(...)`
- 各个 `vector_stores/*.py`

作用：

- 对 query 做 embedding
- 在向量库中检索候选结果
- 结合多信号做排序
- 返回更相关的记忆结果

### 3. Hosted API 客户端

核心目录：

- `mem0/client/`

作用：

- 访问 Mem0 平台 API
- 提供 `MemoryClient` / `AsyncMemoryClient`
- 适合直接接入官方托管服务

### 4. OpenMemory 本地服务

核心目录：

- `openmemory/api/app/`

作用：

- 提供本地 API
- 管理用户、应用、记忆、分类、统计、备份
- 集成 MCP Server

### 5. Provider 可插拔扩展

核心目录：

- `mem0/llms/`
- `mem0/embeddings/`
- `mem0/vector_stores/`
- `mem0/reranker/`
- `mem0/configs/`

作用：

- 屏蔽不同厂商差异
- 通过统一接口切换 provider
- 支持 OpenAI、Anthropic、Ollama、Qdrant、PGVector、FAISS 等

## 技术栈

### Python 后端

- **FastAPI**：提供 API 服务
- **Pydantic v2**：配置和数据模型校验
- **SQLAlchemy**：关系型数据库 ORM
- **Alembic**：数据库迁移（主要用于 `openmemory/api`）
- **Uvicorn**：ASGI 服务启动

### AI / Memory 核心

- **OpenAI / Anthropic / Ollama / Groq / Gemini** 等 LLM provider
- **Qdrant / PGVector / FAISS / Chroma / Weaviate** 等向量存储
- **Embedding + Reranker + Metadata Filter** 组合检索

### 工程化

- **uv**：Python 环境与依赖管理
- **pytest**：测试
- **ruff / isort**：Python 代码规范

## 学习重点/难点

### 重点 1：先分清“SDK”和“服务”

新手最容易搞混：

- `mem0/`：是 SDK
- `openmemory/api/`：是本地服务
- `server/`：是另一个 REST 服务

### 重点 2：先读 `Memory`，不要先读所有 provider

真正的主角是：

- `mem0/memory/main.py`

因为这里串起了：

- 参数校验
- metadata / filter 构建
- LLM 抽取
- 向量写入
- 检索与排序

### 重点 3：Factory 设计是这个项目的扩展核心

关键文件：

- `mem0/utils/factory.py`

它负责根据配置动态创建：

- LLM
- Embedding
- Vector Store
- Reranker

### 重点 4：OpenMemory 是“业务层包装”

如果你想看一个完整后端项目怎么基于 SDK 做业务封装，重点看：

- `openmemory/api/main.py`
- `openmemory/api/app/models.py`
- `openmemory/api/app/routers/memories.py`
- `openmemory/api/app/utils/memory.py`

### 重点 5：部署时要注意外部依赖

特别是 `server/`：

- 不是只装 Python 包就行
- 还依赖数据库、向量库、以及对应驱动
- `psycopg` 在部分环境下需要 `psycopg[binary]`

## 代码阅读顺序

推荐按下面顺序读：

1. `mem0/__init__.py`  
   先看项目对外暴露了哪些核心类。

2. `mem0/memory/main.py`  
   看清 Memory 的核心工作流。

3. `mem0/utils/factory.py`  
   理解 provider 是怎么被动态装配的。

4. `mem0/configs/base.py` + `mem0/configs/*`  
   理解配置结构。

5. `mem0/client/main.py`  
   理解托管平台客户端怎么调用 API。

6. `openmemory/api/main.py`  
   看服务如何启动、建表、挂路由。

7. `openmemory/api/app/models.py`  
   看业务数据模型设计。

8. `openmemory/api/app/routers/memories.py`  
   看最重要的记忆接口实现。

9. `openmemory/api/app/utils/memory.py`  
   看业务层如何构造 Mem0 配置并初始化客户端。

10. `server/main.py`  
    最后再看重型 REST API 服务。

## 总结

> **学习这个项目的正确姿势：先跑 `openmemory/api`，再读 `mem0/memory/main.py`，最后再看 provider 和更重的 `server/`。**

如果你把这个项目拆成一句话：

- **`mem0/` 负责“记忆能力”**
- **`openmemory/api/` 负责“本地业务服务封装”**
- **`server/` 负责“独立 REST API 暴露”**

对新手来说，最有价值的不是一次把所有 provider 看完，而是先把这条主线看懂：

```text
请求进来 → Memory 处理 → Factory 选组件 → 向量库存储/检索 → 服务层返回结果
```
