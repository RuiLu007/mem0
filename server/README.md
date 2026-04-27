# server 目录说明

## 文件夹作用

`server/` 是一个独立的 Mem0 REST API 服务，适合部署成单独后端接口服务。

## 真正入口

- **入口文件：`server/main.py`**

## 核心职责

1. 基于 FastAPI 暴露记忆相关 REST API
2. 在服务启动时创建 `Memory` 实例
3. 使用 pgvector 作为默认向量存储
4. 提供新增、查询、搜索、更新、删除、重置等接口
5. 支持 `ADMIN_API_KEY` 鉴权

## 里面文件的用途

| 文件 | 用途 |
| --- | --- |
| `main.py` | 服务主入口，定义 FastAPI 应用和所有 REST 接口 |
| `requirements.txt` | 当前服务所需 Python 依赖 |
| `.env.example` | 环境变量示例 |
| `Dockerfile` | 生产构建镜像 |
| `dev.Dockerfile` | 开发调试镜像 |
| `docker-compose.yaml` | 启动服务 + PostgreSQL + Neo4j 的开发编排 |
| `Makefile` | Docker 场景下的快捷命令 |

## 启动注意事项

这个目录不是最轻量的学习入口，因为它默认依赖：

- PostgreSQL / pgvector
- OpenAI API Key
- `psycopg[binary]` 运行时支持

如果你只是想先学懂项目，建议先跑：

- `openmemory/api/main.py`

再回来看这里。
