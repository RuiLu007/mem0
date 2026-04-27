# mem0/client 目录说明

## 文件夹作用

`mem0/client/` 是 Mem0 托管平台的 Python 客户端实现。

## 核心职责

1. 封装对 Mem0 Platform HTTP API 的调用
2. 提供同步/异步客户端
3. 管理认证、请求参数、错误处理
4. 支持项目级能力管理

## 里面文件的用途

| 文件 | 用途 |
| --- | --- |
| `main.py` | `MemoryClient` / `AsyncMemoryClient` 主实现 |
| `project.py` | 项目级 API 管理逻辑 |
| `types.py` | 各种请求参数的数据类型定义 |
| `utils.py` | API 错误处理、辅助函数 |
| `__init__.py` | 对外导出客户端类 |

## 适合什么时候看

- 想知道 SDK 如何调用线上平台 API
- 想学习一个 Python API Client 的封装方式
- 想区分 Hosted 模式和 OSS 模式的差异
