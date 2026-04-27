# openmemory/api/app/routers 目录说明

## 文件夹作用

`openmemory/api/app/routers/` 负责按业务模块拆分 API 路由。

## 核心职责

1. 接收 HTTP 请求
2. 参数校验与业务调度
3. 调用数据库和 Mem0 SDK
4. 按模块返回统一接口结果

## 里面文件的用途

| 文件 | 用途 |
| --- | --- |
| `memories.py` | 记忆相关接口，最核心 |
| `apps.py` | 应用列表、应用详情、应用状态管理 |
| `stats.py` | 用户维度统计信息 |
| `config.py` | Mem0 / OpenMemory 配置管理接口 |
| `backup.py` | 记忆导出与备份相关接口 |
| `__init__.py` | 统一导出 router |

## 阅读建议

优先阅读：

1. `memories.py`
2. `config.py`
3. `backup.py`

这样最容易看清业务主流程。
