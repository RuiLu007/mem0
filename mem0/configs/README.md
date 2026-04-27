# mem0/configs 目录说明

## 文件夹作用

`mem0/configs/` 负责定义 Mem0 的配置模型。

## 核心职责

1. 统一管理 Memory 总配置结构
2. 为不同 provider 提供独立配置类
3. 用 Pydantic 做字段校验和默认值管理
4. 保证工厂层能够按统一格式读取配置

## 里面文件/子目录用途

| 路径 | 用途 |
| --- | --- |
| `base.py` | Memory 总配置模型 |
| `enums.py` | 枚举定义 |
| `prompts.py` | 默认提示词配置 |
| `llms/` | LLM provider 配置模型 |
| `embeddings/` | Embedder 配置模型 |
| `vector_stores/` | 向量库配置模型 |
| `rerankers/` | Reranker 配置模型 |
| `__init__.py` | 导出配置模块 |

## 阅读建议

先看 `base.py`，再看各 provider 子目录，这样更容易理解整个配置结构。
