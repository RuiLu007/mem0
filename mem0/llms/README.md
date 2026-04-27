# mem0/llms 目录说明

## 文件夹作用

`mem0/llms/` 存放不同大模型提供方的适配实现。

## 核心职责

1. 把不同 LLM 厂商统一成一致接口
2. 屏蔽不同 SDK 的调用差异
3. 为记忆抽取、总结、结构化输出提供模型能力

## 里面文件的用途

| 文件 | 用途 |
| --- | --- |
| `base.py` | LLM 抽象基类 |
| `openai.py` | OpenAI LLM 实现 |
| `anthropic.py` | Anthropic LLM 实现 |
| `ollama.py` | Ollama 本地模型实现 |
| `groq.py` / `together.py` / `gemini.py` / `deepseek.py` 等 | 其他 provider 实现 |
| `openai_structured.py` / `azure_openai_structured.py` | 结构化输出版本 |
| `configs.py` | 与 LLM 相关的配置支持 |
| `__init__.py` | 模块导出 |

## 学习重点

读这个目录时，不需要一次全看完。  
先挑你最熟悉的一个，比如 `openai.py`，理解统一接口模式即可。
