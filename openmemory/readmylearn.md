# OpenMemory 学习笔记

> 适合 Python 后端初学者 / AI 项目学习者，基于 `openmemory` 子项目整理。

---

## 一、项目介绍

**OpenMemory** 是 [mem0](https://github.com/mem0ai/mem0) 开源项目的**自托管记忆平台**模块。它让 AI 助手拥有持久记忆能力——记住用户说过的话、偏好、习惯等信息，并在下次对话中智能调用。

### 核心价值

| 能力 | 说明 |
|------|------|
| 📝 记忆存储 | 将对话内容提炼为结构化记忆条目 |
| 🔍 语义搜索 | 通过向量相似度检索相关记忆 |
| 🏷️ 自动分类 | 用 GPT 自动给记忆打标签（工作/旅行/健康等） |
| 🔒 权限控制 | 按 App 隔离记忆访问权限 |
| 🤖 MCP 协议 | 让 Claude/Cursor 等 AI 工具通过标准协议调用记忆 |

### 整体组成

```
openmemory/
├── api/          ← 后端 FastAPI 服务（核心，本笔记重点）
├── ui/           ← 前端 Next.js 管理界面
└── docker-compose.yml  ← 一键启动全栈
```

---

## 二、架构设计

### 分层架构图

```
┌─────────────────────────────────────────────────────┐
│                   客户端层                           │
│  Claude / Cursor / 自定义应用  →  MCP / REST API     │
└───────────────────────┬─────────────────────────────┘
                        │ HTTP / SSE / StreamableHTTP
┌───────────────────────▼─────────────────────────────┐
│                  API 层 (FastAPI)                    │
│                                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │ memories │ │   apps   │ │  stats   │ │ config │ │
│  │  router  │ │  router  │ │  router  │ │ router │ │
│  └────┬─────┘ └────┬─────┘ └──────────┘ └────────┘ │
│       │             │                               │
│  ┌────▼─────────────▼──────────────────────────┐   │
│  │              MCP Server                      │   │
│  │  (add/search/delete/list memories via MCP)   │   │
│  └──────────────────────┬──────────────────────┘   │
└─────────────────────────┼───────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────┐
│                  业务逻辑层                          │
│                                                     │
│   get_memory_client()  →  mem0.Memory               │
│   categorization       →  OpenAI GPT-4o-mini        │
│   permissions          →  ACL 规则检查               │
└──────────┬────────────────────┬─────────────────────┘
           │                    │
┌──────────▼──────┐   ┌─────────▼──────────────────────┐
│   关系数据库     │   │      向量数据库                 │
│   SQLite /      │   │  Qdrant（默认）/ Chroma /       │
│   PostgreSQL    │   │  Redis / Milvus / pgvector      │
│   (元数据存储)   │   │  (语义搜索 + Embedding 存储)    │
└─────────────────┘   └────────────────────────────────┘
```

### 数据流转（以「添加记忆」为例）

```
用户对话内容
    ↓
MCP add_memories() / POST /api/v1/memories/
    ↓
get_memory_client() → mem0.Memory.add()
    ↓
[LLM 提炼事实] → [Embedding 向量化] → [写入 Qdrant]
    ↓
[写入 SQLite memories 表（元数据）]
    ↓
[SQLAlchemy event 触发] → [OpenAI 自动分类] → [写入 categories 表]
```

---

## 三、核心功能模块

### 3.1 MCP Server（`app/mcp_server.py`）

> **最核心的文件**，让 AI 工具（Claude/Cursor）能调用记忆。

| 工具方法 | 功能 |
|---------|------|
| `add_memories` | 添加新记忆（支持 LLM 提炼或原文存储） |
| `search_memories` | 语义搜索相关记忆 |
| `list_memories` | 列出所有记忆 |
| `delete_memory` | 删除单条记忆 |
| `delete_all_memories` | 删除全部记忆 |

**重点设计：懒加载 + 容错**
```python
# 不在启动时初始化，避免 Qdrant/Ollama 未就绪时崩溃
def get_memory_client_safe():
    try:
        return get_memory_client()
    except Exception as e:
        logging.warning(f"Failed: {e}")
        return None  # 降级运行，不崩溃
```

### 3.2 Memory Client 管理（`app/utils/memory.py`）

> 负责创建和管理 `mem0.Memory` 实例（单例 + 配置驱动）。

**核心逻辑：**
1. 从环境变量读取 LLM / Embedder / VectorStore 配置
2. 从数据库 `configs` 表读取用户自定义配置（优先级更高）
3. 用 MD5 哈希检测配置是否变化，按需重建客户端
4. Docker 环境自动修正 `localhost` → `host.docker.internal`

### 3.3 记忆 CRUD（`app/routers/memories.py`）

| 路由 | 方法 | 功能 |
|------|------|------|
| `/api/v1/memories/` | GET | 分页列表，支持筛选/搜索/排序 |
| `/api/v1/memories/{id}` | GET | 查单条 |
| `/api/v1/memories/{id}` | PUT | 更新内容 |
| `/api/v1/memories/{id}/state` | PUT | 修改状态（active/paused/archived/deleted） |
| `/api/v1/memories/{id}` | DELETE | 软删除 |

### 3.4 自动分类（`app/utils/categorization.py`）

- 每次记忆写入/更新后，SQLAlchemy `after_insert` / `after_update` 事件自动触发
- 调用 `gpt-4o-mini` 解析记忆归属哪些分类
- 预设 20 个标准分类（Personal / Work / Health / Travel 等），也允许 LLM 自创分类

### 3.5 权限控制（`app/utils/permissions.py`）

```
记忆访问检查流程：
1. 记忆状态必须是 active
2. App 必须存在且未被暂停
3. 查 access_controls 表：
   - 无规则 → 全部可访问
   - allow 规则 → 指定可访问
   - deny 规则 → 指定禁止访问
```

### 3.6 数据库模型（`app/models.py`）

| 表 | 作用 |
|----|------|
| `users` | 用户 |
| `apps` | 接入的 AI 应用（Claude/Cursor 等） |
| `memories` | 记忆条目（核心表） |
| `categories` | 分类标签 |
| `memory_categories` | 记忆↔分类 多对多关联 |
| `access_controls` | ACL 访问控制规则 |
| `archive_policies` | 自动归档策略 |
| `memory_status_history` | 状态变更历史 |
| `memory_access_logs` | 访问日志 |
| `configs` | 系统配置（LLM/Embedder/VectorStore） |

---

## 四、技术栈

### 后端（`api/`）

| 技术 | 版本要求 | 用途 |
|------|---------|------|
| **FastAPI** | ≥0.68 | Web 框架，路由/依赖注入 |
| **SQLAlchemy** | ≥1.4 | ORM，数据库操作 |
| **Alembic** | ≥1.7 | 数据库迁移 |
| **mem0ai** | ≥0.1.92 | 核心记忆引擎（LLM + 向量搜索） |
| **MCP** | ≥1.3 | Model Context Protocol，AI 工具集成 |
| **Qdrant** | - | 默认向量数据库 |
| **OpenAI** | ≥1.40 | 默认 LLM + Embedder |
| **fastapi-pagination** | ≥0.12 | 分页支持 |
| **tenacity** | 9.1.2 | 自动重试（分类接口） |
| **python-dotenv** | - | 环境变量加载 |

### 前端（`ui/`）

| 技术 | 用途 |
|------|------|
| **Next.js 15** | React 框架 |
| **React 19** | UI 库 |
| **TailwindCSS** | 样式 |
| **Redux Toolkit** | 状态管理 |
| **Radix UI** | 无样式组件库 |
| **Recharts** | 图表 |

---

## 五、学习重点 / 难点

### ⭐ 重点一：MCP 协议是什么？

> Model Context Protocol（MCP）是 Anthropic 提出的开放标准，让 AI 工具（Claude、Cursor）能调用外部工具/数据源。

```
Claude ←─── SSE/HTTP ───→ MCP Server（FastAPI）←── 记忆读写 ──→ Qdrant
```

本项目用 `mcp.server.fastmcp.FastMCP` 将 Python 函数直接暴露为 MCP 工具，非常简洁。

### ⭐ 重点二：mem0 记忆引擎工作原理

```python
from mem0 import Memory
m = Memory.from_config(config_dict={
    "llm": {"provider": "openai", "config": {...}},
    "embedder": {"provider": "openai", "config": {...}},
    "vector_store": {"provider": "qdrant", "config": {...}}
})

# 添加：LLM 提炼关键事实 → 向量化 → 存入 Qdrant
m.add("我喜欢喝绿茶", user_id="alice")

# 搜索：问题向量化 → Qdrant 相似度搜索 → 返回相关记忆
m.search("我的饮品偏好", user_id="alice")
```

### ⭐ 重点三：SQLAlchemy 事件监听（自动分类）

```python
# 每次 Memory 插入后自动触发分类
@event.listens_for(Memory, 'after_insert')
def after_memory_insert(mapper, connection, target):
    db = Session(bind=connection)
    categorize_memory(target, db)  # 调用 OpenAI 分类
```

这是 SQLAlchemy 的**事件系统**，不需要手动调用，非常优雅。

### ⭐ 重点四：配置优先级设计

```
环境变量（默认值）
    ↑ 被覆盖
数据库 configs 表（用户通过 UI 保存的配置）
    ↑ 被覆盖
代码中 custom_instructions 参数
```

### ❗ 难点：向量数据库 vs 关系数据库 双写

- **Qdrant（向量库）**：存储 Embedding + 原始文本，负责语义搜索
- **SQLite/PostgreSQL（关系库）**：存储元数据（状态、分类、权限、日志）
- 两者通过 `memory_id`（UUID）关联，但**不强一致**，需理解最终一致性的含义

---

## 六、代码阅读顺序

> 建议按以下顺序阅读，从启动入口逐步深入：

```
第 1 步：api/main.py
    ↓ 了解启动流程：建表 → 创建默认用户 → 挂载 MCP → 注册路由

第 2 步：app/database.py + app/config.py
    ↓ 了解数据库连接和配置读取

第 3 步：app/models.py
    ↓ 了解所有数据表结构及关系

第 4 步：app/utils/memory.py → get_memory_client()
    ↓ 了解 mem0 客户端如何初始化（核心）

第 5 步：app/routers/memories.py
    ↓ 了解记忆的增删改查 REST API

第 6 步：app/mcp_server.py
    ↓ 了解 MCP 工具注册和 AI 工具集成

第 7 步：app/utils/categorization.py
    ↓ 了解 LLM 自动分类实现

第 8 步：app/routers/config.py
    ↓ 了解动态配置系统
```

---

## 七、总结

| 维度 | 评价 |
|------|------|
| **学习价值** | ⭐⭐⭐⭐⭐ 综合了 FastAPI / SQLAlchemy / 向量数据库 / MCP / OpenAI 最佳实践 |
| **代码质量** | 分层清晰，单一职责，有容错降级设计 |
| **扩展性** | 向量库 / LLM / Embedder 均可热替换，通过环境变量或 UI 配置 |
| **适合人群** | 想学 AI 应用后端架构的 Python 工程师 |

**一句话总结：** OpenMemory 是一个用 FastAPI + mem0 + MCP 构建的 AI 记忆中台，核心价值是让任意 AI 工具通过标准协议读写持久化的用户记忆。
