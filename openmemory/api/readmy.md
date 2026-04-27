# api/ — 后端服务目录

> OpenMemory 的核心后端，基于 FastAPI 构建，提供 REST API + MCP Server 双接口。

---

## 文件夹作用

本目录是整个 OpenMemory 的**服务端大脑**：
- 对外暴露 REST API（供前端 UI 调用）
- 对外暴露 MCP Server（供 Claude / Cursor / Codex 等 AI 工具调用）
- 管理所有记忆数据的增删改查、分类、权限、配置

---

## 核心职责

| 职责 | 实现方式 |
|------|---------|
| 记忆的 CRUD | FastAPI 路由 + SQLAlchemy ORM |
| 语义搜索 | mem0ai 库对接 Qdrant 向量数据库 |
| AI 工具集成 | MCP (Model Context Protocol) Server |
| 自动分类 | OpenAI GPT-4o-mini + SQLAlchemy 事件 |
| 权限管理 | ACL 访问控制表 |
| 动态配置 | 数据库 configs 表 + 环境变量 |
| 数据库迁移 | Alembic |

---

## 目录结构及文件用途

```
api/
├── main.py                  ← 🚀 启动入口，注册路由、初始化数据库、挂载 MCP
├── requirements.txt         ← Python 依赖列表
├── .env.example             ← 环境变量模板（复制为 .env 填写 API Key）
├── .python-version          ← Python 版本锁定文件
├── alembic.ini              ← Alembic 迁移配置
├── config.json              ← 运行时配置缓存（可忽略）
├── default_config.json      ← 默认配置模板
├── Dockerfile               ← Docker 构建文件
│
├── alembic/                 ← 数据库迁移脚本目录
│   ├── env.py               ← 迁移环境配置
│   └── versions/            ← 各版本迁移文件
│       ├── 0b53c747049a_initial_migration.py   ← 初始建表
│       ├── add_config_table.py                  ← 新增 configs 表
│       └── afd00efbd06b_add_unique_*.py         ← 添加唯一约束
│
├── app/                     ← 应用核心代码
│   ├── __init__.py
│   ├── config.py            ← 读取 USER_ID / DEFAULT_APP_ID 环境变量
│   ├── database.py          ← SQLAlchemy 引擎、Session、get_db 依赖
│   ├── models.py            ← 所有数据库模型（ORM 表定义 + 事件监听）
│   ├── schemas.py           ← Pydantic 响应模型（API 入参/出参校验）
│   ├── mcp_server.py        ← ⭐ MCP Server 核心，注册 AI 工具接口
│   │
│   ├── routers/             ← API 路由层
│   │   ├── __init__.py      ← 统一导出所有 router
│   │   ├── memories.py      ← /api/v1/memories 记忆 CRUD
│   │   ├── apps.py          ← /api/v1/apps    应用管理
│   │   ├── stats.py         ← /api/v1/stats   统计数据
│   │   ├── config.py        ← /api/v1/config  动态配置读写
│   │   └── backup.py        ← /api/v1/backup  数据备份导出
│   │
│   └── utils/               ← 工具函数层
│       ├── __init__.py
│       ├── memory.py        ← ⭐ mem0 客户端管理（初始化/单例/热重载）
│       ├── categorization.py← 调用 OpenAI 对记忆自动分类
│       ├── db.py            ← get_or_create_user/app 数据库辅助函数
│       ├── permissions.py   ← ACL 权限检查逻辑
│       └── prompts.py       ← LLM Prompt 模板（分类用的 system prompt）
│
└── tests/                   ← 测试目录
    └── test_mcp_server.py   ← MCP Server 接口测试
```

---

## 关键文件详解

### `main.py` — 启动入口

```python
# 启动时做 4 件事：
# 1. 创建数据库所有表
Base.metadata.create_all(bind=engine)
# 2. 创建默认用户和默认 App
create_default_user()
create_default_app()
# 3. 挂载 MCP Server
setup_mcp_server(app)
# 4. 注册所有 REST 路由
app.include_router(memories_router)
```

### `app/models.py` — 数据模型

核心表关系：
```
User ──(1:N)──> App ──(1:N)──> Memory ──(N:M)──> Category
                                  │
                              AccessLog / StatusHistory
```

### `app/utils/memory.py` — mem0 客户端

最复杂的文件，实现了：
- 自动检测向量数据库（Qdrant/Chroma/Redis/pgvector 等 8 种）
- 自动检测 LLM 和 Embedder 配置
- Docker 环境 Ollama URL 自动修正
- 配置哈希对比，避免不必要的重建

### `app/mcp_server.py` — MCP 服务

通过 `@mcp.tool()` 装饰器注册工具，Claude/Cursor 连接后即可调用：
```
MCP 工具列表：add_memories / search_memories / list_memories
             delete_memory / delete_all_memories
```
