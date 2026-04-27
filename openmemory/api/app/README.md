# openmemory/api/app 目录说明

## 文件夹作用

`openmemory/api/app/` 是 OpenMemory 后端的业务代码主目录。

## 核心职责

1. 管理数据库模型和连接
2. 定义 API 路由
3. 封装 Mem0 客户端初始化逻辑
4. 提供权限、分类、提示词、数据库辅助能力
5. 提供 MCP Server 适配

## 里面文件/子目录用途

| 路径 | 用途 |
| --- | --- |
| `models.py` | SQLAlchemy 数据模型定义 |
| `database.py` | 数据库连接和 Session 管理 |
| `schemas.py` | Pydantic 响应/请求模型 |
| `config.py` | OpenMemory 基础配置 |
| `mcp_server.py` | MCP 服务实现与路由挂载 |
| `routers/` | 按模块拆分的 API 路由 |
| `utils/` | 业务辅助工具函数 |
| `__init__.py` | 包初始化 |

## 学习建议

推荐阅读顺序：

1. `database.py`
2. `models.py`
3. `routers/memories.py`
4. `utils/memory.py`
5. `mcp_server.py`
