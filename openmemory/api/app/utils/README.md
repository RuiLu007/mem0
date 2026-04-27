# openmemory/api/app/utils 目录说明

## 文件夹作用

`openmemory/api/app/utils/` 存放 OpenMemory 业务层的辅助逻辑。

## 核心职责

1. 初始化和缓存 Mem0 客户端
2. 处理用户 / 应用创建逻辑
3. 管理权限校验
4. 生成分类和提示词相关辅助内容

## 里面文件的用途

| 文件 | 用途 |
| --- | --- |
| `memory.py` | 初始化 Mem0 `Memory` 实例，自动拼装 provider 配置 |
| `db.py` | 用户和应用的查询/创建辅助函数 |
| `permissions.py` | 记忆权限校验 |
| `categorization.py` | 记忆自动分类逻辑 |
| `prompts.py` | 提示词相关内容 |
| `__init__.py` | 包初始化 |

## 学习建议

这里最值得重点看的是：

- `memory.py`

因为它直接体现了“业务服务如何接 SDK”。
