# routers/ — API 路由层

> 接收 HTTP 请求，参数校验，调用业务逻辑，返回响应。每个文件对应一组相关接口。

---

## 文件夹作用

路由层是 REST API 的入口，采用 FastAPI 的 `APIRouter` 组织，按资源类型拆分文件，最终在 `main.py` 统一注册。

---

## 文件用途

### `__init__.py` — 统一导出

```python
from .apps import router as apps_router
from .memories import router as memories_router
# ...统一导出，main.py 一次性引入
```

---

### `memories.py` — 记忆核心接口 ⭐

**路径前缀：** `/api/v1/memories`

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/` | 分页列表，支持按用户/App/时间/分类筛选，支持关键词搜索 |
| GET | `/{id}` | 获取单条记忆详情 |
| PUT | `/{id}` | 更新记忆内容或元数据 |
| PUT | `/{id}/state` | 修改记忆状态（active/paused/archived/deleted） |
| DELETE | `/{id}` | 软删除记忆（修改状态为 deleted，不物理删除） |
| POST | `/actions/search` | 语义搜索（调用 mem0 向量搜索） |
| DELETE | `/` | 批量删除（按用户/App） |

**重要辅助函数：**
- `get_accessible_memory_ids(db, app_id)` — 根据 ACL 规则返回可访问的记忆 ID 集合
- `update_memory_state(db, memory_id, new_state, user_id)` — 更新状态并记录历史

---

### `apps.py` — 应用管理接口

**路径前缀：** `/api/v1/apps`

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/` | 列出所有 App，附带记忆数量、访问次数统计 |
| GET | `/{id}` | 获取单个 App 详情 |
| PUT | `/{id}/pause` | 暂停 App（该 App 无法再访问记忆） |
| PUT | `/{id}/resume` | 恢复 App |

**设计说明：** App 代表一个接入 OpenMemory 的客户端（如 Claude、Cursor 等），暂停后其记忆访问权限失效。

---

### `stats.py` — 统计接口

**路径前缀：** `/api/v1/stats`

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/` | 返回用户的记忆总数、App 总数、App 列表 |

---

### `config.py` — 动态配置接口

**路径前缀：** `/api/v1/config`

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/` | 获取当前配置（LLM/Embedder/VectorStore/自定义指令） |
| POST | `/` | 保存新配置，自动触发 mem0 客户端重建 |

**配置结构示例：**
```json
{
  "openmemory": { "custom_instructions": "请用中文提炼记忆要点" },
  "mem0": {
    "llm": { "provider": "openai", "config": { "model": "gpt-4o-mini" } },
    "embedder": { "provider": "openai", "config": { "model": "text-embedding-3-small" } },
    "vector_store": { "provider": "qdrant", "config": { "host": "localhost", "port": 6333 } }
  }
}
```

---

### `backup.py` — 备份接口

**路径前缀：** `/api/v1/backup`

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/export` | 导出所有记忆数据（JSON 格式） |
