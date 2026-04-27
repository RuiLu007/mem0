# alembic/ — 数据库迁移目录

> 管理数据库表结构的版本历史，类似 Git 管理代码，Alembic 管理数据库 Schema。

---

## 文件夹作用

当数据库表结构需要变更时（新增字段、新增表、修改约束等），通过 Alembic 迁移脚本**安全地**升级/回滚，不需要手动写 SQL。

---

## 核心职责

- 记录每次数据库结构变更
- 提供 `upgrade` / `downgrade` 双向操作（可回滚）
- 保证团队协作时数据库结构一致

---

## 文件用途

| 文件/目录 | 说明 |
|----------|------|
| `../alembic.ini` | Alembic 主配置，指定数据库连接字符串和脚本路径 |
| `env.py` | 迁移运行环境配置，连接数据库、加载 ORM Base |
| `script.py.mako` | 新迁移脚本的模板文件 |
| `versions/` | 所有迁移版本脚本，按时间顺序链式执行 |

---

## versions/ — 迁移版本

| 文件 | 说明 |
|------|------|
| `0b53c747049a_initial_migration.py` | 初始建表：users / apps / memories / categories 等所有核心表 |
| `add_config_table.py` | 新增 `configs` 表，用于存储 LLM/向量库动态配置 |
| `afd00efbd06b_add_unique_user_id_constraints.py` | 给 `users.user_id` 添加唯一约束 |

---

## 常用命令

```bash
# 升级到最新版本
uv run alembic upgrade head

# 回滚一个版本
uv run alembic downgrade -1

# 查看当前版本
uv run alembic current

# 查看所有版本历史
uv run alembic history
```

> ⚠️ 注意：本项目在 `main.py` 启动时直接调用 `Base.metadata.create_all()` 建表，**不强制使用 Alembic**。Alembic 主要用于生产环境结构变更管理。
