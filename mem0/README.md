# mem0 目录说明

## 文件夹作用

`mem0/` 是整个 Python 项目的核心 SDK 源码目录，真正的“长期记忆能力”都在这里。

## 核心职责

1. 对外暴露 `Memory`、`AsyncMemory`、`MemoryClient`、`AsyncMemoryClient`
2. 负责记忆写入、检索、更新、删除等主流程
3. 统一管理 LLM、Embedding、向量库、Reranker 的适配与装配
4. 提供配置模型、异常、工具函数和扩展机制

## 里面文件/子目录用途

| 路径 | 用途 |
| --- | --- |
| `__init__.py` | 对外导出最核心的 SDK 类 |
| `memory/` | 自托管记忆主逻辑，最重要的目录 |
| `client/` | 官方托管平台 API 客户端 |
| `configs/` | 配置模型定义 |
| `llms/` | 各种 LLM provider 实现 |
| `embeddings/` | 各种 Embedding provider 实现 |
| `vector_stores/` | 各种向量数据库适配 |
| `reranker/` | 检索结果重排能力 |
| `utils/` | 工厂、实体抽取、评分等通用工具 |
| `exceptions.py` | 项目自定义异常 |
| `proxy/` | 代理相关实现 |

## 学习建议

如果你第一次读这个目录，优先顺序是：

1. `__init__.py`
2. `memory/main.py`
3. `utils/factory.py`
4. `configs/`
5. `client/`
6. 再看 `llms/`、`embeddings/`、`vector_stores/`
