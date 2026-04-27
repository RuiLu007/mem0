# mem0/embeddings 目录说明

## 文件夹作用

`mem0/embeddings/` 负责把文本转换成向量。

## 核心职责

1. 统一不同 embedding provider 的调用方式
2. 为记忆写入和搜索提供向量表示
3. 让上层 Memory 逻辑不关心底层模型实现差异

## 里面文件的用途

| 文件 | 用途 |
| --- | --- |
| `base.py` | Embedder 抽象基类 |
| `openai.py` | OpenAI Embedding 实现 |
| `ollama.py` | Ollama Embedding 实现 |
| `huggingface.py` | HuggingFace Embedding 实现 |
| `fastembed.py` | FastEmbed 实现 |
| `gemini.py` / `vertexai.py` / `aws_bedrock.py` 等 | 其他 provider 实现 |
| `mock.py` | Mock embedding，适合特殊场景或测试 |
| `configs.py` | 嵌入模型相关配置 |
| `__init__.py` | 模块导出 |

## 学习重点

读完 `base.py` 和 `openai.py` 后，再去看其他 provider，理解成本最低。
