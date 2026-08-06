# Qdrant 向量数据库部署与使用指南

本文说明如何在 `platform-agent-service` 中部署 [Qdrant](https://github.com/qdrant/qdrant)，以及如何把项目文件 / 业务文本写入向量库，并在 Agent 代码中检索使用。

## 1. 架构位置

| 组件       | 职责                          | 默认地址                          |
| ---------- | ----------------------------- | --------------------------------- |
| Postgres   | LangGraph Checkpointer / 会话 | `127.0.0.1:16543`                 |
| **Qdrant** | 向量存储与语义检索（RAG）     | **REST `http://127.0.0.1:16333`** |
| Agent 服务 | FastAPI + LangGraph           | `PORT`（默认 8009）               |

数据流：

```text
本地文件 / 业务文本
    → Embedding（DashScope qwen3.7-text-embedding，OpenAI 兼容）
    → Qdrant Collection（payload 含原文 text + source）
    → similarity_search(query)
    → 拼成上下文，注入 Prompt / Tool 结果
```

当前阶段已提供：**Docker 部署、客户端封装、入库脚本、代码内检索 API**。  
尚未把检索结果自动挂到每一轮 chat（避免在未确认策略前改动 HITL / Plan 链路）。需要 RAG 时，在业务代码中调用 `VectorStoreService`（见 §5）。

## 2. 部署（Docker Compose）

配置文件：[`docker-compose.yml`](../../deploy/docker-compose.yml)。

| 映射                         | 说明                     |
| ---------------------------- | ------------------------ |
| 宿主机 **16333** → 容器 6333 | REST API + Web Dashboard |
| 宿主机 **16334** → 容器 6334 | gRPC（大批量写入可选）   |
| Volume `agent_qdrant_data`   | 持久化向量数据           |

### 2.1 启动

在仓库根目录：

```bash
bash scripts/up.sh
# 或：docker compose -f deploy/docker-compose.yml up -d

docker compose -f deploy/docker-compose.yml ps
curl -s http://127.0.0.1:16333/readyz
```

浏览器打开 Dashboard：<http://127.0.0.1:16333/dashboard>

### 2.2 环境变量

复制 / 更新 `.env`（参考 `.env.example`）：

```bash
QDRANT_URL=http://127.0.0.1:16333
# QDRANT_API_KEY=          # 本地 compose 默认无鉴权；生产建议开启
QDRANT_COLLECTION=platform_agent_docs
QDRANT_VECTOR_SIZE=1024
EMBEDDING_PROVIDER=dashscope
EMBEDDING_MODEL=qwen3.7-text-embedding
VECTOR_CHUNK_SIZE=800
VECTOR_CHUNK_OVERLAP=120

# Embedding 需要厂商 Key（与聊天共用）
DASHSCOPE_API_KEY=sk-...
```

说明：

- **`QDRANT_VECTOR_SIZE` 必须与 Embedding 维度一致**。DashScope `qwen3.7-text-embedding` 默认 1024；若改模型维度，需新建 collection（或删除旧 collection 后重建）。
- 留空 `QDRANT_URL` 可禁用向量能力；`GET /health` 中 `qdrant.enabled=false`。

### 2.3 安装 Python 依赖

```bash
uv sync
# 或：uv sync --extra dev
```

依赖项：`qdrant-client`（见 `pyproject.toml`）。Embedding 复用已有 `langchain-openai`（DashScope compatible-mode）。

### 2.4 健康检查

启动 Agent 后：

```bash
curl -s http://127.0.0.1:8009/health | python -m json.tool
```

关注字段：

```json
{
  "qdrant": {
    "enabled": true,
    "ok": true,
    "url": "http://127.0.0.1:16333",
    "collections": ["platform_agent_docs"],
    "error": ""
  }
}
```

### 2.5 常用运维命令

```bash
# 以下命令均在仓库根目录执行（compose 文件在 deploy/）
COMPOSE="docker compose -f deploy/docker-compose.yml"

# 查看日志
$COMPOSE logs -f qdrant

# 停止 / 启动
$COMPOSE stop qdrant
$COMPOSE start qdrant

# 销毁容器但保留数据卷
$COMPOSE down

# ⚠️ 连同数据卷一起删除（不可恢复）
$COMPOSE down -v
```

## 3. 如何把项目文件 / 数据写入向量库

### 3.1 推荐：入库脚本

脚本：[`scripts/ingest_to_qdrant.py`](../scripts/ingest_to_qdrant.py)

```bash
# 仓库根目录先起依赖
bash scripts/up.sh
cd services/platform-agent-service
uv sync

# 单个文件
uv run python scripts/ingest_to_qdrant.py --file docs/qdrant-deployment.md

# 整个目录（默认递归 .md/.txt/.py/.json/.mdc/.yaml/.yml/.ts/.tsx/.rst）
uv run python scripts/ingest_to_qdrant.py --dir ../../prj-docs

# 入库后立刻试检索
uv run python scripts/ingest_to_qdrant.py \
  --dir ../../prj-docs \
  --search "告警确认流程" \
  --limit 5

# JSON 输出（便于脚本消费）
uv run python scripts/ingest_to_qdrant.py --search "BPMN 编排" --json
```

行为说明：

1. 读取 UTF-8 文本 → 按 `VECTOR_CHUNK_SIZE` / `VECTOR_CHUNK_OVERLAP` 切块
2. 调用 Embedding API 生成向量
3. Upsert 到 `QDRANT_COLLECTION`；payload 至少包含：`text`、`source`、`filename`、`chunk_index`
4. Point ID 由「collection + source + chunk 内容」哈希生成，**重复入库同一片段会覆盖**（幂等）

跳过：`.venv`、`node_modules`、`__pycache__`、`.git`、`dist`、`build` 及非 UTF-8 文件。

### 3.2 在代码中入库

```python
from pathlib import Path
from app.infrastructure.vector.store import VectorStoreService

store = VectorStoreService()
store.ensure_collection()

# 纯文本
store.upsert_texts(
    ["值班员可通过侧栏 AI 助手批量确认告警。"],
    metadatas=[{"source": "manual", "category": "ops"}],
)

# 单文件
store.ingest_file(Path("docs/qdrant-deployment.md"))

# 目录（默认可靠替换；返回 files / failed）
result = store.ingest_directory(Path("../../prj-docs"))
print(result.chunk_total, len(result.failed))
```

### 3.3 用 Dashboard / HTTP API 手工写入（调试）

Dashboard：<http://127.0.0.1:16333/dashboard>

或 REST（需自行提供已算好的向量）：

```bash
curl -X PUT "http://127.0.0.1:16333/collections/platform_agent_docs/points?wait=true" \
  -H "Content-Type: application/json" \
  -d '{
    "points": [
      {
        "id": "11111111-1111-1111-1111-111111111111",
        "vector": [0.01, 0.02],
        "payload": {"text": "示例", "source": "manual"}
      }
    ]
  }'
```

注意：向量维度必须等于 collection 的 `size`（默认 1024）。生产入库请走脚本 / `VectorStoreService`，由 Embedding 模型生成向量。

### 3.4 建议入库的内容

| 类型              | 示例路径                                   | 用途                                                         |
| ----------------- | ------------------------------------------ | ------------------------------------------------------------ |
| 产品 / 业务知识库 | `prj-docs/*.md` / `docs/architecture/*.md` | 能力说明、操作指引 RAG                                       |
| Agent 提示词      | `platform-agent-service/app/prompts/*.md`  | 检索增强（慎用，避免泄漏内部约束到用户可见回复时需二次过滤） |
| 平台 API 索引摘要 | `app/data/platform_api_index.json`         | 工具选型辅助（体积大时先摘要再入库）                         |
| 值班 SOP / 知识库 | 业务侧导出的 `.md` / `.txt`                | 问答助手                                                     |

## 4. 如何在项目中检索使用

### 4.1 直接检索

```python
from app.infrastructure.vector.store import VectorStoreService

store = VectorStoreService()
hits = store.similarity_search("如何导出告警", limit=5)

for hit in hits:
    print(hit.score, hit.payload.get("source"), hit.text[:80])

# 拼成可注入 Prompt 的上下文
context = store.format_context(hits, max_chars=4000)
```

### 4.2 在 Agent 节点 / Tool 中使用（扩展点）

示例：在自定义 Server Tool 或 Plan 步骤前检索知识：

```python
from app.infrastructure.vector.client import is_qdrant_configured, probe_qdrant
from app.infrastructure.vector.store import VectorStoreService

def retrieve_knowledge(question: str) -> str:
    if not is_qdrant_configured() or not probe_qdrant().get("ok"):
        return ""
    store = VectorStoreService()
    hits = store.similarity_search(question, limit=4)
    return store.format_context(hits)
```

将 `retrieve_knowledge(user_message)` 的返回值拼入 system / human 消息即可做简易 RAG。  
若要做成正式 Tool，请按现有规范走：`packages/agent-core/tool-catalog.ts` → `export_catalog.py` → handler → i18n。

### 4.3 模块索引

| 模块      | 路径                                      | 说明                                          |
| --------- | ----------------------------------------- | --------------------------------------------- |
| 配置      | `app/config.py`                           | `qdrant_*` / `embedding_*` / `vector_chunk_*` |
| 客户端    | `app/infrastructure/vector/client.py`     | 单例、`probe_qdrant`                          |
| Embedding | `app/infrastructure/vector/embeddings.py` | DashScope / DeepSeek OpenAI 兼容              |
| 切块      | `app/infrastructure/vector/chunking.py`   | 字符窗口 + 重叠                               |
| 存储服务  | `app/infrastructure/vector/store.py`      | 建库 / 入库 / 检索                            |
| 入库 CLI  | `scripts/ingest_to_qdrant.py`             | 文件与目录批量写入                            |

## 5. 常见问题

**Q: `/readyz` 通，但入库报 API Key 错误？**  
A: Qdrant 只存向量；生成向量需要 `DASHSCOPE_API_KEY`（或对应 `EMBEDDING_PROVIDER` 的 Key）。

**Q: 改了 `QDRANT_VECTOR_SIZE` 后报 dimension mismatch？**  
A: 删除旧 collection 后重建：

```bash
curl -X DELETE http://127.0.0.1:16333/collections/platform_agent_docs
uv run python scripts/ingest_to_qdrant.py --dir ../../prj-docs
```

**Q: 生产环境安全？**  
A: 当前 compose **未开启 API Key**，仅适合本机 / 内网。生产请配置 Qdrant 鉴权、TLS，并设置 `QDRANT_API_KEY`，勿将 Dashboard 暴露公网。

**Q: 与 Postgres 的关系？**  
A: 互不替代。Postgres 存会话 / checkpoint；Qdrant 存语义向量。二者都由 `bash scripts/up.sh`（或 `docker compose -f deploy/docker-compose.yml up -d`）拉起。

## 6. 参考

- Qdrant 仓库：<https://github.com/qdrant/qdrant>
- Qdrant 文档：<https://qdrant.tech/documentation/>
- Python 客户端：`qdrant-client`
- LangChain VectorStore 概念：<https://docs.langchain.com/oss/python/integrations/vectorstores/index>
