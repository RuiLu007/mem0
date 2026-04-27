# utils/ — 工具函数层

> 所有核心业务逻辑都在这里，路由层只负责接收请求，真正的"脏活"交给 utils。

---

## 文件夹作用

将业务逻辑从路由中解耦，便于复用和测试。主要提供：
- mem0 记忆客户端的生命周期管理
- LLM 自动分类能力
- 数据库常用操作封装
- 权限校验逻辑
- LLM Prompt 模板管理

---

## 文件详解

---

### `memory.py` — mem0 客户端管理 ⭐⭐⭐⭐⭐

**这是整个项目最复杂、最核心的工具文件。**

#### 主要函数

| 函数 | 功能 |
|------|------|
| `get_memory_client()` | 获取（或初始化）mem0 Memory 单例 |
| `reset_memory_client()` | 强制重置客户端（配置变更后调用） |
| `get_default_memory_config()` | 从环境变量自动构建默认配置 |
| `_get_docker_host_url()` | Docker 环境下自动解析宿主机 IP |
| `_fix_ollama_urls()` | 将 localhost Ollama URL 替换为 Docker 宿主机地址 |
| `_parse_environment_variables()` | 将配置中的 `"env:OPENAI_API_KEY"` 替换为实际值 |

#### 自动检测支持的向量数据库

| 触发环境变量 | 对应向量库 |
|------------|----------|
| `QDRANT_HOST` + `QDRANT_PORT` | Qdrant（默认） |
| `CHROMA_HOST` + `CHROMA_PORT` | Chroma |
| `WEAVIATE_CLUSTER_URL` | Weaviate |
| `REDIS_URL` | Redis |
| `PG_HOST` + `PG_PORT` | pgvector |
| `MILVUS_HOST` + `MILVUS_PORT` | Milvus |
| `ELASTICSEARCH_HOST` | Elasticsearch |
| `OPENSEARCH_HOST` | OpenSearch |
| `FAISS_PATH` | FAISS（本地文件） |

#### 配置加载优先级

```
1. 环境变量（默认值）         ← 最低优先级
2. 数据库 configs 表          ← 用户在 UI 中保存的设置
3. custom_instructions 参数   ← 最高优先级（代码调用时指定）
```

---

### `categorization.py` — 自动分类

**调用 OpenAI `gpt-4o-mini`，将记忆内容归类到标准分类体系。**

```python
# 使用示例
categories = get_categories_for_memory("我今天跑步5公里，感觉很好")
# 返回：["health", "personal"]
```

**设计亮点：**
- `@retry(stop_after_attempt(3))` — 自动重试 3 次，应对 OpenAI 网络抖动
- `response_format=MemoryCategories` — 强制结构化输出，不用解析字符串

---

### `permissions.py` — 权限检查

**检查一个 App 是否有权访问指定记忆。**

```
检查流程：
1. 记忆状态必须是 active（paused/archived/deleted 均不可访问）
2. 如果不传 app_id，只检查记忆状态
3. App 必须存在且 is_active=True
4. 查询 access_controls 表：
   - 无规则 → 全部放行
   - 有 allow 规则（object_id=NULL）→ 全部放行
   - 有 deny 规则（object_id=NULL）→ 全部拒绝
   - 有具体 ID 规则 → 精确控制
```

---

### `db.py` — 数据库辅助函数

**封装「不存在则创建」的常用操作，避免路由层重复代码。**

| 函数 | 功能 |
|------|------|
| `get_or_create_user(db, user_id)` | 按 user_id 查用户，不存在则创建 |
| `get_or_create_app(db, user, app_id)` | 按 owner+name 查 App，不存在则创建 |
| `get_user_and_app(db, user_id, app_id)` | 一次性获取用户和 App（MCP Server 常用） |

---

### `prompts.py` — LLM Prompt 模板

**存放 System Prompt，集中管理，便于修改调试。**

当前只有一个：`MEMORY_CATEGORIZATION_PROMPT`

预设 20 个标准分类（Personal / Work / Health / Travel / Finance 等），并允许 LLM 自行创建新分类。
