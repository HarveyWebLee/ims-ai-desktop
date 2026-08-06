# 05 — Qdrant 知识库（RAG）增删改查

> 编码与运维以本文为准。实现入口：`app/infrastructure/vector/store.py`；CLI：`uv run kb`（或 `scripts/ingest_to_qdrant.py`）。

## 1. 角色与数据流

知识库存平台文档、操作指引、能力说明，供 Agent：

1. **被动注入**：每轮 `assemble_context` 对用户消息做语义检索，拼入「参考知识」（单条截断，见 `AGENT_RAG_PASSIVE_SNIPPET_CHARS`）
2. **主动工具**：`retrieve_knowledge(query, top_k?)`（Agent 本地工具；P1-3 经 Subagent **摘要**回主 agent，不含全文 hits）

```text
文档/目录
  → 切块 (chunking)
  → Embedding (DashScope qwen3.7-text-embedding, 1024 维)
  → Qdrant Collection (platform_knowledge)
  → 对话检索 / CLI 检索 / retrieve_knowledge
```

`QDRANT_URL` 为空：跳过注入；工具返回「未配置」。

---

## 2. 部署与配置

```bash
# 仓库根目录
bash scripts/up.sh
# 或：docker compose -f deploy/docker-compose.yml up -d
```

| 项        | 值                               |
| --------- | -------------------------------- |
| REST      | `http://127.0.0.1:16333`         |
| Dashboard | http://127.0.0.1:16333/dashboard |
| Volume    | `agent_qdrant_data`              |

`.env` 关键项：

```bash
QDRANT_URL=http://127.0.0.1:16333
QDRANT_COLLECTION=platform_knowledge
QDRANT_VECTOR_SIZE=1024          # 须与 Embedding 维度一致；qwen3.7-text-embedding 默认 1024
EMBEDDING_PROVIDER=dashscope
EMBEDDING_MODEL=qwen3.7-text-embedding
DASHSCOPE_API_KEY=...
VECTOR_CHUNK_SIZE=800
VECTOR_CHUNK_OVERLAP=120
RAG_TOP_K=4
```

改维度或改 Embedding 模型后：**须删库重建**（见 §删 → drop collection），旧向量不可混用。文本模型走 DashScope **OpenAI compatible-mode**；仅 `qwen3-vl-embedding` 走多模态原生 API。

---

## 3. 数据模型

### Collection

| 名称                         | 距离   | 维度 | 用途     |
| ---------------------------- | ------ | ---- | -------- |
| `platform_knowledge`（默认） | Cosine | 1024 | 知识正文 |

### Point（一条 chunk）

| 字段                          | 说明                                                                                                                 |
| ----------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `id`                          | 稳定 UUID：`sha256(collection\|doc_id\|chunk_index\|text)` 前 32 hex → UUID。**同内容重复入库会覆盖**（幂等 upsert） |
| `vector`                      | Embedding 向量                                                                                                       |
| `payload.text`                | 原文片段                                                                                                             |
| `payload.source`              | 规范化绝对路径（POSIX 分隔符 `/`）                                                                                   |
| `payload.doc_id`              | 稳定文档键：在 `KNOWLEDGE_DOCS_DIR`/`prj-docs` 下为相对路径，否则 `abs:`+哈希                                        |
| `payload.chunk_index`         | 切块序号                                                                                                             |
| `payload.media_kind`          | `document` / `table` / `image` / `text`                                                                              |
| `payload.filename` / `suffix` | 文件名与后缀                                                                                                         |
| `payload.title`               | 可选标题                                                                                                             |

**重要**：删除/替换优先认 `doc_id`，并兼容 `source` 路径变体。文件入库务必落在同一文档根，否则会出现「删不掉旧数据」。

---

## 4. 增（Create / Ingest）

### 4.1 含义

任意目录层级下的知识文件 → **多格式抽文本** → 切块 → Embedding → `upsert`。  
集合不存在时自动 `ensure_collection`。

### 4.2 支持的格式与目录

| 类别             | 后缀                                            | 说明                                                                                  |
| ---------------- | ----------------------------------------------- | ------------------------------------------------------------------------------------- |
| 文本 / Markdown  | `.md` `.txt` `.rst` …                           | 多编码尝试                                                                            |
| Word / PPT / PDF | `.docx` `.pptx` `.pdf`                          | 含文内表格（Markdown 化）                                                             |
| **表格文件**     | **`.xlsx` `.xls` `.csv` `.tsv`**                | 转为 Markdown 表格后向量化；单表最多 `KNOWLEDGE_TABLE_MAX_ROWS` 行（默认 2000）       |
| **图片**         | **`.png` `.jpg` `.jpeg` `.gif` `.webp` `.bmp`** | DashScope VL（默认 `qwen-vl-plus`）抽文字/描述 → 再 Embedding；需 `DASHSCOPE_API_KEY` |
| 网页             | `.html` `.htm`                                  | 去标签                                                                                |

**目录**：默认 `glob=**/*`，任意层级；跳过 `.git` / `node_modules` / `.venv` 等。

**图片向量化链路**：

```text
图片文件 → DashScope 视觉模型（OCR + 图意描述）→ 纯文本
        → 切块 → qwen3.7-text-embedding → Qdrant
```

**表格向量化链路**：

```text
xlsx/xls/csv → 解析行列 → Markdown 表格文本 → 切块 → Embedding → Qdrant
```

相关环境变量：

```bash
KNOWLEDGE_VISION_ENABLED=true
KNOWLEDGE_VISION_MODEL=qwen-vl-plus
KNOWLEDGE_VISION_TIMEOUT_SECONDS=120
KNOWLEDGE_VISION_MAX_SIDE=1280
KNOWLEDGE_IMAGE_MAX_BYTES=8388608
KNOWLEDGE_TABLE_MAX_ROWS=2000
DASHSCOPE_API_KEY=...
```

**不支持 / 需转换**：

- `.doc` / `.ppt` → 另存为 `.docx` / `.pptx`
- 扫描版 PDF 几乎无文字层时，可先导出为图片再入库（走 VL）
- 音视频：知识库未启用 ASR

未知后缀：默认跳过；CLI `--try-unknown` 尝试文本解码。

实现：`extractors.py`（分发）+ `vision.py`（图片 VL）。

### 4.3 CLI

```bash
cd platform-agent-service

uv run kb --file ./手册.docx
uv run kb --file ./报表.xlsx --file ./架构图.png
uv run kb --dir D:/知识库
uv run kb --dir D:/知识库 --ext .xlsx --ext .png --ext .jpg
uv run kb --dir D:/知识库 --try-unknown
uv run kb --search "如何确认告警"
uv run kb --count
uv run kb --replace-file ./手册.docx
```

### 4.4 代码

```python
from pathlib import Path
from app.infrastructure.vector.store import VectorStoreService

store = VectorStoreService()
store.ensure_collection()

store.ingest_file(Path("手册.docx"))
store.ingest_directory(
    Path("D:/知识库"),
    glob="**/*",           # 任意层级
    try_unknown=False,     # True=尝试未知后缀文本
)
# 仅 Word + PPT
store.ingest_directory(Path("D:/知识库"), suffixes={".docx", ".pptx", ".md"})
```

### 4.5 行为说明

- **默认可靠替换**：`--file` / `--dir` / `ingest_file` / HTTP 上传均先 upsert 再删同 `doc_id`（及 source 变体）下未覆盖的旧点，避免幽灵知识
- 仅追加写（不推荐）：CLI `--no-replace` 或 `ingest_file(..., replace=False)`
- 相同 `(doc_id, chunk_index, text)` → **同一 id**，再次入库为覆盖写
- 抽取失败的文件：**记入失败列表并跳过**，不中断整目录入库；CLI 会打印失败路径
- `upsert_texts` 按 `VECTOR_UPSERT_BATCH_SIZE`（默认 64）分批 embedding + upsert，避免单次 HTTP JSON 超过 Qdrant 32MB 限制
- 审计孤儿：`uv run kb --audit` 或 `GET /api/agent/knowledge/audit`（库内有向量但磁盘文件不存在）

---

## 5. 查（Read / Search / List）

### 5.1 语义检索（主路径）

对查询句 Embedding，在 collection 内 Cosine top-k。

```bash
# 仅检索
uv run kb --search "如何确认告警" --limit 5

# JSON 输出
uv run kb --search "BPMN 条件图" --json

# 限制来源子串
uv run kb --search "MCP" --source-contains architecture
```

```python
hits = store.similarity_search("如何确认告警", limit=5, score_threshold=None)
for h in hits:
    print(h.id, h.score, h.payload.get("source"), h.text[:80])

ctx = store.format_context(hits, max_chars=4000)  # 拼进 Prompt 用
```

Agent 侧：

| 入口                      | 行为                                                                                               |
| ------------------------- | -------------------------------------------------------------------------------------------------- |
| `assemble_context`        | 调用 `retrieve_knowledge_blocks(user_message)`，截断注入参考知识                                   |
| `retrieve_knowledge` 工具 | Agent 主动检索 → Subagent 摘要（`summary` + `sources`，不含全文 hits）                             |
| 语音转写后纠错            | 见 [`10-voice-asr.md`](./10-voice-asr.md)：Realtime **按段**并发纠错；HTTP/Oneshot 回传 `segments` |

相关环境变量（转写纠错 / 流式并行 / Realtime，默认开启）：

```bash
TRANSCRIBE_RAG_ENABLED=true
TRANSCRIBE_DICTIONARY_ENABLED=true
TRANSCRIBE_RAG_TOP_K=2
TRANSCRIBE_CORRECT_MODEL=qwen-flash
TRANSCRIBE_CORRECT_TIMEOUT_SECONDS=6
TRANSCRIBE_CORRECT_MIN_SCORE=0.42
TRANSCRIBE_CORRECT_SNIPPET_CHARS=160
TRANSCRIBE_CORRECT_MAX_TOKENS=48
TRANSCRIBE_CORRECT_CACHE_TTL_SECONDS=2592000
REDIS_URL=redis://127.0.0.1:13386/0
TRANSCRIBE_STREAM_ENABLED=true
TRANSCRIBE_PIPELINE_WORKERS=4
TRANSCRIBE_REALTIME_ENABLED=true
TRANSCRIBE_REALTIME_MODEL=qwen3-asr-flash-realtime
TRANSCRIBE_REALTIME_WS_URL=wss://dashscope.aliyuncs.com/api-ws/v1/realtime
```

流水线：`Rule → Redis Cache → Dictionary → Vector → LLM`（低成本优先退出；**按 ASR 落定段触发**，Realtime **无**终稿全文再纠）。  
协议与桌面标注开关：[`10-voice-asr.md`](./10-voice-asr.md)。  
实现：`app/services/voice/`；词典：`app/data/asr_dictionary.json`。

### 5.2 浏览 / 计数（非语义）

```bash
uv run kb --count
uv run kb --list --limit 20
uv run kb --list --source "E:/WORK/CODE/ims-ai-desktop/docs/architecture/00-overview.md"
```

```python
print(store.count())
hits, next_offset = store.scroll_points(limit=20, source_equals=abs_path)
```

### 5.3 健康检查

`GET http://127.0.0.1:8008/health` → `qdrant.enabled / ok / collections`。

---

## 6. 改（Update）

知识库没有「改某一字段」的业务 API，更新策略是：

| 场景                       | 做法                                                               |
| -------------------------- | ------------------------------------------------------------------ |
| **同一 chunk 文本未变**    | 再 `ingest` / `upsert_texts` 即可（幂等覆盖）                      |
| **文件内容或切块结果变了** | **整文件替换**：先按 `source` 删光旧点，再入库                     |
| **只改元数据**             | 目前需删后重建；或直接 `upsert` 同 id 带新 payload（代码层可扩展） |

### 6.1 CLI（推荐）

```bash
# 等价于：delete_by_source(绝对路径) + ingest_file
uv run kb --replace-file ../docs/architecture/00-overview.md
```

### 6.2 代码

```python
store.replace_file(Path("../docs/architecture/00-overview.md"))
# 内部：
#   source = str(path.resolve())
#   delete_by_source(source)
#   ingest_file(path)
```

**不要**只对改过的文件再跑一次 `--file` 而不 `--replace-file`：若切块数量减少，多出来的旧 chunk 仍会参与检索，造成「幽灵知识」。

---

## 7. 删（Delete）

### 7.1 按来源删除（常用）

`source` 必须与入库时一致（文件一般为 **resolve 后的绝对路径**）。

```bash
# Windows / 本机请先用 --list 确认 source 字符串
uv run kb --list --limit 5

uv run kb --delete-source "E:/WORK/CODE/ims-ai-desktop/docs/architecture/00-overview.md"
```

```python
store.delete_by_source(str(Path(".../00-overview.md").resolve()))
```

### 7.2 按 Point ID 删除

```bash
uv run kb --delete-id "<uuid>" --delete-id "<uuid2>"
```

```python
store.delete_by_ids(["aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"])
```

### 7.3 删除整个 Collection（危险）

维度变更、Embedding 模型更换、全量重建时使用。

```bash
uv run kb --drop-collection --yes
# 然后重新 --dir / --file 入库
```

```python
store.drop_collection()
store.ensure_collection()
```

---

## 8. CLI 参数速查

| 参数                               | 类别  | 说明                                 |
| ---------------------------------- | ----- | ------------------------------------ |
| `--file`                           | 增    | 入库文件（默认可靠替换）             |
| `--dir` / `--glob`                 | 增    | 递归任意层级（默认可靠替换）         |
| `--no-replace`                     | 增    | 仅追加 upsert（不推荐）              |
| `--ext`                            | 增    | 限定后缀，如 `--ext .docx`           |
| `--try-unknown`                    | 增    | 未知后缀尝试文本解码                 |
| `--replace-file`                   | 改    | 显式可靠替换（与默认 `--file` 等价） |
| `--search` / `--limit`             | 查    | 语义检索                             |
| `--count`                          | 查    | 点数                                 |
| `--list`                           | 查    | 浏览                                 |
| `--audit`                          | 查    | 孤儿文档审计                         |
| `--source`                         | 查/删 | source 精确匹配                      |
| `--source-contains`                | 查    | source 子串                          |
| `--delete-source`                  | 删    | 按来源删（含变体与 doc_id）          |
| `--delete-id`                      | 删    | 按 id 删                             |
| `--drop-collection --yes`          | 删    | 删库                                 |
| `--collection`                     | 通用  | 覆盖集合名                           |
| `--chunk-size` / `--chunk-overlap` | 增/改 | 切块                                 |
| `--json`                           | 通用  | JSON 汇总输出                        |

---

## 9. 代码模块位置

```text
platform-agent-service/
  app/infrastructure/vector/
    client.py       # Qdrant 单例、probe_qdrant
    embeddings.py   # Embedding
    chunking.py     # 切块
    extractors.py   # ★ 多格式抽文本（docx/pptx/pdf/xlsx/csv/图片…）
    vision.py       # ★ 图片 → DashScope VL → 文本
    source_keys.py  # source / doc_id 规范化
    store.py        # ★ CRUD（默认可靠替换、孤儿审计）
  app/rag/
    store.py        # 再导出 VectorStoreService
    context.py      # 对话侧 retrieve_knowledge_blocks / format_rag_section
  scripts/ingest_to_qdrant.py   # CLI
```

| API | 方法                                                                                   |
| --- | -------------------------------------------------------------------------------------- |
| 增  | `ensure_collection`、`upsert_texts`、`ingest_file`（默认 replace）、`ingest_directory` |
| 查  | `similarity_search`、`scroll_points`、`count`、`format_context`、`audit_orphans`       |
| 改  | `ingest_file_replacing` / `replace_file`；同内容 `upsert_*` 幂等覆盖                   |
| 删  | `delete_by_ids`、`delete_by_source`、`delete_by_doc_id`、`drop_collection`             |

### HTTP 运营 API（P1-5，需登录）

桌面「设置 → 知识与术语」调用；清空 collection 须登录 + `{ confirm: true }`（文档/实体分集合）。

| 方法   | 路径                                   | 说明                                                                             |
| ------ | -------------------------------------- | -------------------------------------------------------------------------------- |
| GET    | `/api/agent/knowledge/stats`           | 点数 / 连通性                                                                    |
| GET    | `/api/agent/knowledge/audit`           | 孤儿文档审计（库内有向量、磁盘 source 缺失）                                     |
| GET    | `/api/agent/knowledge/documents`       | 按 source 聚合（含 `doc_id` / `file_exists`）                                    |
| GET    | `/api/agent/knowledge/points`          | 浏览片段（`limit`、`source_contains`）                                           |
| POST   | `/api/agent/knowledge/search`          | 语义试检索 `{ query, limit? }`                                                   |
| POST   | `/api/agent/knowledge/ingest`          | multipart 上传后**可靠替换**入库（返回 chunks / deleted_before / doc_id）        |
| POST   | `/api/agent/knowledge/replace`         | multipart：`file` + `source`，保留原 source 键更新                               |
| POST   | `/api/agent/knowledge/export`          | `{ source }` → 导出正文供本地下载（优先磁盘，否则拼接片段）                      |
| DELETE | `/api/agent/knowledge/by-source`       | `{ source }` 删除（路径变体 + `doc_id`）                                         |
| POST   | `/api/agent/knowledge/drop-collection` | `{ confirm: true }` 清空文档知识 collection（换 Embedding 后重建；磁盘文件保留） |

实体同步可观测：

| 方法 | 路径                                  | 说明                                                                          |
| ---- | ------------------------------------- | ----------------------------------------------------------------------------- |
| POST | `/api/agent/entity-sync`              | 触发同步（达梦只读 SELECT）                                                   |
| GET  | `/api/agent/entity-sync/status`       | 最近一次结果 + `in_progress` + `persisted` + `checkpoints`（Postgres 可恢复） |
| POST | `/api/agent/entities/drop-collection` | `{ confirm: true }` 清空实体术语 collection                                   |

实现：`app/api/knowledge.py`、`app/api/entity_sync.py`、`app/sync/entity_sync_status.py`、`app/infrastructure/persistence/entity_sync_repository.py`。  
水位线/成败只写 **Agent Postgres**（`entity_sync_status` / `entity_sync_checkpoint`），**禁止**在平台达梦写同步标记。

---

## 10. 运维建议

1. **入库前**：`bash scripts/up.sh` + `curl`/`GET /health` 看 `qdrant.ok`
2. **文档更新流水线**：改文档后直接 `--file` / `--dir`（默认可靠替换）或设置页上传；定期 `--audit` 查孤儿
3. **全量重建**：`--drop-collection --yes` → `--dir ../docs/architecture` → `--dir ../../prj-docs`
4. **排错**：Dashboard 看 points；CLI `--list` / `--audit` 核对 `source`/`doc_id`；检索无结果时检查 Embedding Key 与维度
5. **安全**：生产环境清库须经登录态 + `confirm=true`；运营 HTTP 提供 `drop-collection`（文档/实体分集合），勿挂无人值守任务；换 Embedding 模型或维度后**必须**先清对应 collection 再全量重建。

---

## 11. 与对话链路的关系

```text
用户消息
  → assemble_context
  → retrieve_knowledge_blocks (similarity_search, top_k=RAG_TOP_K)
  → format_rag_section → 拼进 llm_user_message
  → classify / Plan / ReAct（工具仍走 Platform MCP）
```

检索失败或未配置：**静默跳过**，不阻断对话。
