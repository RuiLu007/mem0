# OpenMemory 完整启动指南（uv 版）

> 适用系统：Ubuntu（全新环境）  
> Python 管理工具：`uv`  
> 启动入口文件：`openmemory/api/main.py`

---

## 一、前置准备

### 1.1 安装 uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env  # 或重开终端
uv --version  # 验证安装成功
```

### 1.2 安装 Docker（启动 Qdrant 向量数据库）

```bash
# Ubuntu 安装 Docker
sudo apt update && sudo apt install -y docker.io docker-compose
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER  # 免 sudo 运行 docker
# 重新登录终端或执行：newgrp docker
```

---

## 二、项目依赖安装

```bash
# 进入后端目录
cd /root/01userprofile_ai/mem0/openmemory/api

# 用 uv 创建虚拟环境并安装依赖
uv venv .venv --python 3.11
source .venv/bin/activate

# 安装所有依赖
uv pip install -r requirements.txt
```

---

## 三、环境配置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env，填写你的 OpenAI Key
nano .env
```

**最简 `.env` 配置（仅 OpenAI）：**

```env
OPENAI_API_KEY=sk-你的真实APIKey
USER=default_user
```

**使用 Ollama 本地模型（可选，无需 API Key）：**

```env
USER=default_user
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1:latest
EMBEDDER_PROVIDER=ollama
EMBEDDER_MODEL=nomic-embed-text
OLLAMA_BASE_URL=http://localhost:11434
```

---

## 四、启动 Qdrant 向量数据库

```bash
# 后台启动 Qdrant（向量数据库，存储 Embedding）
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -v qdrant_storage:/qdrant/storage \
  qdrant/qdrant

# 验证 Qdrant 是否正常运行
curl http://localhost:6333/healthz
# 返回 {"title":"qdrant - vector search engine","version":"..."} 即为正常
```

---

## 五、数据库初始化

> **本项目无需手动运行 Alembic 迁移**，FastAPI 启动时会自动建表。  
> 默认使用 SQLite（`openmemory.db`），无需额外安装数据库服务。

如需使用 PostgreSQL（生产环境推荐）：

```bash
# .env 中添加
DATABASE_URL=postgresql://user:password@localhost:5432/openmemory
```

---

## 六、启动后端服务

```bash
# 确保在 api/ 目录，且虚拟环境已激活
cd /root/01userprofile_ai/mem0/openmemory/api
source .venv/bin/activate

# 启动 FastAPI 服务（开发模式，自动重载）
uv run uvicorn main:app --host 0.0.0.0 --port 8765 --reload
```

**启动成功标志：**

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
Auto-detected vector store: qdrant with config: ...
Auto-detected LLM provider: openai
Memory client initialized successfully
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8765
```

**验证服务正常：**

```bash
curl http://localhost:8765/docs
# 浏览器打开 http://localhost:8765/docs 查看 Swagger API 文档
```

---

## 七、启动前端 UI（可选）

```bash
# 需要先安装 Node.js 和 pnpm
sudo apt install -y nodejs npm
npm install -g pnpm

cd /root/01userprofile_ai/mem0/openmemory/ui
pnpm install

# 创建前端环境变量
echo "NEXT_PUBLIC_API_URL=http://localhost:8765" > .env.local
echo "NEXT_PUBLIC_USER_ID=default_user" >> .env.local

pnpm run dev
# 浏览器访问 http://localhost:3000
```

---

## 八、一键 Docker Compose 启动（全栈）

> 最简单的方式，自动启动 Qdrant + 后端 API + 前端 UI

```bash
cd /root/01userprofile_ai/mem0/openmemory

# 创建 api/.env
cp api/.env.example api/.env
# 编辑 api/.env 填写 OPENAI_API_KEY

# 一键启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止
docker-compose down
```

**服务地址：**

| 服务 | 地址 |
|------|------|
| 后端 API | http://localhost:8765 |
| API 文档 | http://localhost:8765/docs |
| 前端 UI | http://localhost:3000 |
| Qdrant 控制台 | http://localhost:6333/dashboard |

---

## 九、MCP 接入配置（连接 Claude / Cursor）

在 Claude Desktop 的 `claude_desktop_config.json` 中添加：

```json
{
  "mcpServers": {
    "openmemory": {
      "url": "http://localhost:8765/mcp/sse/?user_id=default_user&client_name=claude"
    }
  }
}
```

在 Cursor 的 MCP 配置中添加：

```json
{
  "mcpServers": {
    "mem0": {
      "url": "http://localhost:8765/mcp/sse/?user_id=default_user&client_name=cursor"
    }
  }
}
```

---

## 十、常见问题排查

### ❌ `Memory client initialized` 报错（向量库连不上）

```bash
# 检查 Qdrant 是否运行
docker ps | grep qdrant
# 若无，重新启动
docker start qdrant
```

### ❌ `OPENAI_API_KEY` 未设置

```bash
# 检查 .env 文件
cat api/.env | grep OPENAI
# 确保没有多余空格，Key 格式为 sk-xxx
```

### ❌ `psycopg2` 安装失败

```bash
# 使用纯 Python 版本（开发环境用 SQLite 不需要 psycopg2）
uv pip install psycopg2-binary
```

### ❌ `ModuleNotFoundError: No module named 'app'`

```bash
# 确保在 api/ 目录下运行命令
cd /root/01userprofile_ai/mem0/openmemory/api
uv run uvicorn main:app ...
```

---

## 附：项目目录结构速览

```
openmemory/
├── api/                    ← 后端（FastAPI）
│   ├── main.py             ← 🚀 启动入口
│   ├── requirements.txt    ← Python 依赖
│   ├── .env.example        ← 环境变量模板
│   └── app/
│       ├── mcp_server.py   ← MCP 协议服务
│       ├── models.py       ← 数据库模型
│       ├── routers/        ← REST API 路由
│       └── utils/          ← 业务逻辑
├── ui/                     ← 前端（Next.js）
└── docker-compose.yml      ← 全栈一键启动
```
