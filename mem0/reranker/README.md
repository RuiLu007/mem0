# mem0/reranker 目录说明

## 文件夹作用

`mem0/reranker/` 用于对检索结果做二次重排，提高返回结果相关性。

## 核心职责

1. 对向量检索结果进行再排序
2. 支持不同 reranker provider
3. 提升最终召回结果质量

## 里面文件的用途

| 文件 | 用途 |
| --- | --- |
| `base.py` | Reranker 抽象基类 |
| `cohere_reranker.py` | Cohere 重排实现 |
| `huggingface_reranker.py` | HuggingFace 重排实现 |
| `llm_reranker.py` | 基于 LLM 的重排实现 |
| `sentence_transformer_reranker.py` | Sentence Transformer 重排实现 |
| `zero_entropy_reranker.py` | Zero Entropy 重排实现 |
| `__init__.py` | 模块导出 |

## 学习建议

这个目录不是第一优先级。  
先理解 Memory 主流程，再回来读 reranker，会更容易看懂它存在的意义。
