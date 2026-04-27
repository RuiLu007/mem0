# mem0/vector_stores 目录说明

## 文件夹作用

`mem0/vector_stores/` 是 Mem0 的向量数据库适配层。

## 核心职责

1. 对接不同向量数据库
2. 统一插入、搜索、删除、重置等操作接口
3. 让上层 Memory 逻辑可以按配置切换底层存储

## 里面文件的用途

| 文件 | 用途 |
| --- | --- |
| `base.py` | 向量库抽象接口 |
| `qdrant.py` | Qdrant 适配 |
| `pgvector.py` | PostgreSQL + pgvector 适配 |
| `faiss.py` | FAISS 本地向量索引适配 |
| `chroma.py` | Chroma 适配 |
| `weaviate.py` / `milvus.py` / `pinecone.py` / `redis.py` 等 | 其他向量库适配 |
| `configs.py` | 向量库相关配置支持 |
| `__init__.py` | 模块导出 |

## 学习重点

最推荐优先看：

1. `base.py`
2. `qdrant.py`
3. `pgvector.py`

这 3 个最能代表这个目录的设计思路。
