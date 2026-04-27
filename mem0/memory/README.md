# mem0/memory 目录说明

## 文件夹作用

`mem0/memory/` 是 Mem0 Python SDK 的核心实现目录，负责真正的记忆处理流程。

## 核心职责

1. 管理 `Memory` / `AsyncMemory` 的主流程
2. 做参数校验、过滤条件构建、metadata 处理
3. 调用 LLM 提取记忆
4. 调用 Embedder 和 Vector Store 完成写入与检索
5. 处理本地配置、SQLite 历史存储、埋点等辅助逻辑

## 里面文件的用途

| 文件 | 用途 |
| --- | --- |
| `main.py` | 核心主流程，最值得重点阅读 |
| `base.py` | 记忆能力的抽象基类 |
| `setup.py` | 本地配置目录与用户标识初始化 |
| `storage.py` | 本地 SQLite 管理 |
| `telemetry.py` | 埋点和遥测逻辑 |
| `utils.py` | 消息解析、过滤器处理等工具函数 |
| `__init__.py` | 子模块导出 |

## 阅读重点

重点看 `main.py` 里的这些能力：

- `Memory.from_config(...)`
- `add(...)`
- `search(...)`
- `get_all(...)`
- filter / metadata 构建
- provider 初始化
