# 09 — 平台业务库只读约束与实体同步方案

> **强制约束**：智能化功能开发与运行时，对平台业务关系库（达梦）**严格禁止任何写操作**，仅允许查询（`SELECT`）。  
> 编码与评审以本文为准；与 [`05-qdrant-rag.md`](./05-qdrant-rag.md)、[`02-mcp-platform-server.md`](./02-mcp-platform-server.md) 配套。

---

## 1. 目标与边界

### 1.1 目标

1. 明确「平台业务库」与「Agent 自有基础设施」的读写边界。
2. 在**只读**前提下，将设备 / 变量等主数据同步到 Qdrant，支撑语义检索。
3. 为开发、Code Review、运维账号授权提供可执行清单。

### 1.2 适用范围（智能化相关）

下列工程与能力均受本约束约束：

| 范围                              | 说明                               |
| --------------------------------- | ---------------------------------- |
| `services/platform-agent-service` | RAG、实体同步、会话编排、Gateway   |
| `services/platform-mcp-server`    | 平台工具执行面                     |
| `apps/desktop` AiAssistant        | 桌面端智能化交互（M1 无 BPMN UI）  |
| 本地脚本、定时任务、联调工具      | 凡服务智能化功能、连接平台业务库者 |

### 1.3 数据库分类（必须区分）

| 类别             | 实例（示例）                                        | 智能化侧权限  | 说明                           |
| ---------------- | --------------------------------------------------- | ------------- | ------------------------------ |
| **平台业务库**   | 达梦 `192.168.x.x:5236`，业务 schema（如设备/变量） | **仅 SELECT** | 本文禁写对象                   |
| **Agent 自有库** | Postgres `:16543`（checkpointer / 同步水位线）      | 可读可写      | 非平台业务库                   |
| **向量库**       | Qdrant `:16333`                                     | 可读可写      | 非关系业务库；实体向量写入合法 |
| **缓存**         | Redis `:13386`                                      | 可读可写      | 非平台业务库                   |

> **一句话**：禁写的是**平台达梦业务数据**；Agent 自己的 Postgres / Qdrant / Redis **不在禁写范围内**（否则会话与向量同步无法工作）。

### 1.4 非目标

- 不替代平台业务服务对达梦的正常 CRUD（配置管理、设备台账等仍由平台服务写入）。
- 不要求智能化链路「永远不改业务数据」——**写业务必须走平台 API + HITL**，不得由 Agent/MCP/同步脚本直连达梦执行。
- 不在本文穷举全部业务表字段；已知主数据表见 §3.0，其余表走通用行映射。

---

## 2. 强制规则

### 2.1 硬性禁止（平台业务达梦）

对平台业务达梦连接，**禁止**出现任何会改变库状态的语句或副作用，包括但不限于：

| 类别             | 示例                                                           |
| ---------------- | -------------------------------------------------------------- |
| DML              | `INSERT` / `UPDATE` / `DELETE` / `MERGE` / `REPLACE`           |
| DDL              | `CREATE` / `ALTER` / `DROP` / `TRUNCATE` / `COMMENT ON`        |
| 权限与会话副作用 | `GRANT` / `REVOKE` / `CREATE USER`                             |
| 过程副作用       | 调用含写库逻辑的存储过程 / 包 / 函数                           |
| 锁与维护         | 显式写锁意图、批量维护任务、导入导出写回                       |
| 「同步消费」写回 | 在业务库更新 `consumed_at`、写 outbox 已消费标记、写同步状态表 |

**一律不允许**「临时写一下再改回」「调试用 INSERT」「为同步方便在达梦建触发器/outbox 并由智能化账号写入」等例外。若业务侧需要 outbox，须由**平台业务方**建表与触发器；智能化侧**只读消费**，消费进度记在 **Agent Postgres**。

### 2.2 仅允许

| 允许           | 说明                                   |
| -------------- | -------------------------------------- |
| `SELECT`       | 含 `JOIN` / 子查询 / 分页              |
| 只读视图查询   | `SELECT ... FROM V_xxx`                |
| 元数据只读查询 | 如查表结构（若账号具备），不得改元数据 |
| 只读事务       | 若驱动支持，连接属性设为 read-only     |

### 2.3 业务写入的正确路径

```text
用户意图（如改设备名、下发指令）
  → Agent / HITL
  → Platform MCP
  → 平台业务 API（PLATFORM_API_BASE）
  → 平台服务写达梦
```

智能化进程**不得**绕过平台 API 直连达梦做写操作。

### 2.4 账号与连接要求

1. 使用**独立只读账号**（或对智能化账号仅授予 `SELECT`）。
2. 连接串 / 驱动层开启 **readOnly**（能开则必须开）。
3. 凭据仅存各服务本机 / 部署密钥（`.env`、密钥管理），**禁止**写入 git、架构文档正文、聊天记录。
4. JDBC 形态示例（达梦，非 MySQL）：

```text
jdbc:dm://<host>:5236
```

Python 侧使用官方只读连接参数（host / port / user / password），库名与 schema 以现场为准。  
**禁止**用 `jdbc:mysql://` 误连达梦。

---

## 3. 只读前提下的实体 → 向量同步方案

### 3.0 已知业务表与同步表配置

| 业务 | 达梦表名            | 说明                                |
| ---- | ------------------- | ----------------------------------- |
| 设备 | `p_device`          | 专用文本模板（编码/名称等）         |
| 变量 | `p_device_variable` | 专用文本模板（设备编码 + 变量名等） |

环境变量 **`ENTITY_SYNC_TABLES`** 控制「哪些表要转成向量」：

| 配置值                       | 行为                                                     |
| ---------------------------- | -------------------------------------------------------- |
| 空 / 未设置                  | **不执行**任何表数据转换                                 |
| `*`                          | 将当前连接用户可见的**全部表**转换（受每表行数上限约束） |
| `p_device,p_device_variable` | 仅转换列出的表（英文逗号分隔，大小写不敏感）             |
| 列表中含不存在的表           | **提示/返回 missing_tables**，**存在的表仍照常转换**     |

侧栏「同步到向量库」按钮调用 `POST /api/agent/entity-sync`，按上述配置执行一次全量转换（只读拉达梦 → 写 Qdrant）。

推荐本地配置示例：

```bash
ENTITY_SYNC_TABLES=p_device,p_device_variable
```

### 3.1 架构

```text
平台达梦（设备 / 变量等）          Agent 自有基础设施
        │ 只读 SELECT                    │
        ▼                                ▼
┌───────────────────────┐      ┌─────────────────────┐
│ EntityDbSyncWorker    │─────▶│ Postgres            │
│ （platform-agent）    │      │ sync checkpoint     │
│                       │      └─────────────────────┘
│ 拼 text → Embedding   │
│ upsert / delete       │─────▶ Qdrant platform_entities
└───────────────────────┘
        │
        ▼
RAG：assemble_context / retrieve_knowledge
（精确实时查询仍走 Platform MCP → 平台 API）
```

### 3.2 Collection 与主键

| 项          | 约定                                                               |
| ----------- | ------------------------------------------------------------------ |
| Collection  | `platform_entities`（与文档库 `platform_knowledge` 分离）          |
| 设备 source | `dm:device:{deviceCode}`                                           |
| 变量 source | `dm:variable:{deviceCode}:{varCode}`                               |
| Point ID    | 由 `collection + entity_type + 业务键` 稳定哈希，**不含**正文 text |

更新时：同 ID `upsert` 覆盖向量与 payload。  
删除时：`delete_by_source`；删设备时级联删 `dm:variable:{code}:*`。

### 3.3 增量策略（无写达梦）

水位线与对账状态**只存在 Agent Postgres**：

```text
entity_sync_checkpoint(
  stream_name,      -- device | variable
  watermark_ts,
  watermark_id,
  last_full_at,
  updated_at
)
```

周期任务：

1. `SELECT` 达梦中 `UPDATE_TIME`（或等价字段）大于水位线的行。
2. 映射为自然语言 `text` + payload → 写入 Qdrant。
3. 推进 **Postgres** 水位线（不写达梦）。

软删字段（若有）：增量 `SELECT` 到已删标记 → Qdrant `delete_by_source`。  
物理删除：增量不可见 → **定时全量对账**（只读拉全量有效主键集合 ↔ Qdrant source 差集删除）。

### 3.4 明确不做的同步设计

| 方案                                                 | 结论                                                            |
| ---------------------------------------------------- | --------------------------------------------------------------- |
| 达梦触发器 + outbox，智能化账号 `UPDATE consumed_at` | **禁止**（写业务库）                                            |
| 智能化账号在达梦建同步状态表                         | **禁止**                                                        |
| CDC 需在库内落消费位点                               | 消费位点放 Agent Postgres；CDC 若必须写库则不采用，改水位线轮询 |

若平台方自行提供只读变更视图 / 只读 outbox，智能化侧可 `SELECT` 消费，进度仍记在 Agent 侧。

### 3.5 与实时工具的关系

| 能力                             | 路径                                                |
| -------------------------------- | --------------------------------------------------- |
| 语义检索「东门门禁」「温度点位」 | Qdrant `platform_entities`                          |
| 精确列表 / 详情 / 实时值 / 下发  | Platform MCP → 平台 API（平台服务写达梦）           |
| 文档手册 RAG                     | Qdrant `platform_knowledge`（文件入库，与达梦无关） |

---

## 4. 代码与工程落点（约定）

```text
platform-agent-service/
  app/infrastructure/db/
    dameng_readonly.py     # 只读连接；强制 read_only；禁止暴露 execute_write
  app/sync/
    table_config.py        # 解析 ENTITY_SYNC_TABLES
    entity_mapper.py       # 行 → text / payload（含 p_device / p_device_variable）
    entity_sync_service.py # 按配置全量同步
  app/infrastructure/vector/
    entity_store.py        # upsert_entity / delete_by_source
  app/api/entity_sync.py   # POST /api/agent/entity-sync
```

### 4.1 连接封装约束

- 对外只提供 `fetch_all` / `fetch_one` / `stream_query` 类 API。
- **不提供** `execute` / `commit` 写接口；静态检查与 Code Review 拒绝新增。
- SQL 字符串入库前校验：拒绝匹配写关键字的语句（防御性，不替代账号权限）。

### 4.2 环境变量（示例名，无密钥）

```bash
# 平台业务达梦（只读）
DM_HOST=
DM_PORT=5236
DM_USER=          # 只读账号
DM_PASSWORD=      # 仅密钥库 / 本机 .env
DM_SCHEMA=
DM_READ_ONLY=true # 必须为 true；启动时若为 false 则拒绝同步

# 表选择：空=不同步；*=全部表；逗号分隔=指定表
ENTITY_SYNC_TABLES=p_device,p_device_variable
ENTITY_SYNC_MAX_ROWS_PER_TABLE=5000
QDRANT_COLLECTION_ENTITIES=platform_entities

# 可选：JDBC 驱动路径（未安装 dmPython 时使用 JayDeBeApi）
# DM_JDBC_JAR=D:/dmdbms/drivers/jdbc/DmJdbcDriver18.jar
```

---

## 5. 开发与评审门禁

### 5.1 开发自检

- [ ] 新增达梦访问是否仅 `SELECT`？
- [ ] 是否误用业务账号或可写权限？
- [ ] 同步状态是否写在 Agent Postgres / 仅内存，而非达梦？
- [ ] 业务写操作是否仍走 Platform MCP → 平台 API？
- [ ] 文档 / 注释是否出现真实密码？

### 5.2 Code Review 否决项

出现下列任一情况，**直接打回**：

1. 智能化相关代码对平台达梦执行非 `SELECT`。
2. 为「方便同步」申请可写账号或扩大权限。
3. 在达梦创建智能化专用写表 / 触发器（应由平台方决策且非智能化账号写入）。
4. 将达梦密码提交进仓库或写进架构/设计文档。

### 5.3 运行时建议

- 使用只读账号；即使应用层 bug 也无法写库。
- 定期用只读账号尝试 `INSERT` 探活（应失败）作为权限回归（运维侧，非业务功能）。

---

## 6. 与现有架构文档的关系

| 文档                                                       | 关系                              |
| ---------------------------------------------------------- | --------------------------------- |
| [`00-overview.md`](./00-overview.md)                       | 索引纳入本文                      |
| [`01-system-context.md`](./01-system-context.md)           | 数据面增加「平台达梦只读」说明    |
| [`02-mcp-platform-server.md`](./02-mcp-platform-server.md) | 业务写仍只经平台 API              |
| [`05-qdrant-rag.md`](./05-qdrant-rag.md)                   | 文档知识库 CRUD；实体库见本文 §3  |
| [`08-dev-guide.md`](./08-dev-guide.md)                     | 本地环境变量补充 DM\_\*（无密码） |

Cursor 规则：`.cursor/rules/platform-db-readonly.mdc`（与本文同步）。

---

## 7. 修订记录

| 日期       | 说明                                                                   |
| ---------- | ---------------------------------------------------------------------- |
| 2026-07-27 | 初版：平台达梦只读硬约束 + 只读实体同步方案                            |
| 2026-07-27 | 增补：`p_device` / `p_device_variable`、`ENTITY_SYNC_TABLES`、侧栏触发 |
