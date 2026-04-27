# openmemory/api 目录说明

## 文件夹作用

`openmemory/api/` 是 OpenMemory 的 Python 后端服务目录，也是这个仓库里 **最适合本地学习和用 uv 跑通的 Python 服务**。

## 真正入口

- **入口文件：`openmemory/api/main.py`**

## 核心职责

1. 提供 OpenMemory 的 FastAPI 后端接口
2. 自动初始化 SQLite 数据库
3. 管理用户、应用、记忆、分类、统计、备份
4. 集成 MCP Server，支持外部 AI 客户端接入
5. 通过 `app/utils/memory.py` 把 Mem0 SDK 接进业务层

## 里面文件/子目录用途

| 路径 | 用途 |
| --- | --- |
| `main.py` | 服务主入口，创建 FastAPI 应用并挂载路由 |
| `app/` | 主要业务代码 |
| `tests/` | API 与 MCP 相关测试 |
| `alembic/` | Alembic 迁移脚本 |
| `alembic.ini` | Alembic 配置 |
| `requirements.txt` | 当前服务依赖 |
| `.env.example` | 环境变量模板 |
| `Dockerfile` | Docker 镜像构建 |

## 为什么适合新手先读这个目录

因为它具备完整后端项目的典型结构：

- 有入口 `main.py`
- 有 ORM 模型
- 有 router 分层
- 有 utils 辅助层
- 有 MCP 接口
- 有测试

同时它默认用 SQLite，首次导入就能自动建表，学习成本最低。
