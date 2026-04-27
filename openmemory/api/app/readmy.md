# app/ — 应用核心代码目录

> FastAPI 应用的所有业务逻辑都在这里，是整个后端最重要的目录。

---

## 文件夹作用

`app/` 是 FastAPI 应用的主体，按照**分层架构**组织：

```
请求进来 → routers（路由层） → utils（业务逻辑层） → models（数据层）
```

---

## 核心职责

- **路由层**（`routers/`）：接收 HTTP 请求，参数校验，调用业务逻辑，返回响应
- **工具层**（`utils/`）：核心业务逻辑，包括 mem0 客户端管理、分类、权限
- **数据层**（`models.py` + `database.py`）：ORM 模型定义，数据库连接管理
- **协议层**（`mcp_server.py`）：MCP 协议服务，AI 工具集成

---

## 文件用途速查

| 文件 | 类型 | 一句话说明 |
|------|------|-----------|
| `__init__.py` | 包标识 | 空文件，标识这是 Python 包 |
| `config.py` | 配置 | 读取 `USER_ID`、`DEFAULT_APP_ID` 环境变量 |
| `database.py` | 数据库 | 创建 SQLAlchemy engine、SessionLocal、`get_db` 依赖注入函数 |
| `models.py` | 数据模型 | 定义所有 ORM 表 + SQLAlchemy 事件（自动分类触发器） |
| `schemas.py` | 数据校验 | Pydantic 模型：API 请求体/响应体的字段类型定义 |
| `mcp_server.py` | MCP服务 | 注册 MCP 工具函数，处理 AI 工具的 SSE/HTTP 连接 |

---

## routers/ — 路由层

| 文件 | 路径前缀 | 主要功能 |
|------|---------|---------|
| `memories.py` | `/api/v1/memories` | 记忆的增删改查、状态变更、分页列表、批量操作 |
| `apps.py` | `/api/v1/apps` | 应用列表查询、暂停/恢复应用、访问统计 |
| `stats.py` | `/api/v1/stats` | 用户统计数据（记忆总数、应用总数） |
| `config.py` | `/api/v1/config` | 读写系统配置（LLM/Embedder/VectorStore 设置） |
| `backup.py` | `/api/v1/backup` | 记忆数据导出备份 |
| `__init__.py` | - | 统一导出所有 router，供 `main.py` 引入 |

---

## utils/ — 工具层

| 文件 | 一句话说明 | 重要程度 |
|------|-----------|---------|
| `memory.py` | **mem0 客户端单例管理**，自动检测配置，支持热重载 | ⭐⭐⭐⭐⭐ |
| `categorization.py` | 调用 `gpt-4o-mini` 解析记忆类别，返回标签列表 | ⭐⭐⭐⭐ |
| `permissions.py` | 检查 App 是否有权访问指定记忆（ACL 逻辑） | ⭐⭐⭐ |
| `db.py` | `get_or_create_user/app` 数据库辅助函数 | ⭐⭐⭐ |
| `prompts.py` | 存放分类 LLM 的 System Prompt 模板 | ⭐⭐ |

---

## 数据模型关系图

```
┌──────────┐      ┌──────────┐      ┌──────────────┐
│  users   │─1:N─▶│   apps   │─1:N─▶│   memories   │
└──────────┘      └──────────┘      └──────┬───────┘
                                           │ N:M
                                    ┌──────▼───────┐
                                    │  categories  │
                                    └──────────────┘
                                           
memories ──1:N──▶ memory_status_history  (状态变更记录)
memories ──1:N──▶ memory_access_logs     (访问日志)
apps     ──1:N──▶ access_controls        (ACL 规则)
apps     ──1:N──▶ archive_policies       (归档策略)
configs            (独立表，存储 LLM/向量库配置)
```

---

## 重要设计模式

### 1. 依赖注入（FastAPI Depends）

```python
# database.py 定义
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# routers 中使用
@router.get("/")
async def list_memories(db: Session = Depends(get_db)):
    ...  # db 由 FastAPI 自动注入，用完自动关闭
```

### 2. 事件驱动自动分类（SQLAlchemy Events）

```python
# models.py
@event.listens_for(Memory, 'after_insert')
def after_memory_insert(mapper, connection, target):
    # Memory 写入数据库后自动触发，调用 OpenAI 分类
    categorize_memory(target, db)
```

### 3. 单例 + 热重载（mem0 客户端）

```python
# utils/memory.py
_memory_client = None
_config_hash = None

def get_memory_client():
    current_hash = _get_config_hash(config)
    if _memory_client is None or _config_hash != current_hash:
        _memory_client = Memory.from_config(config)  # 仅配置变更时重建
    return _memory_client
```
