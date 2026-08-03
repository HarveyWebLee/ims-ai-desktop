# 11 — 生产级声纹识别（Speaker Recognition）

> 编码依据。声纹是 **语音输入前的身份门禁与说话人识别**，与 ASR / 纠错解耦，不进入 LangGraph / SSE 对话主链。  
> ASR 管线见 [`10-voice-asr.md`](./10-voice-asr.md)。向量基础设施复用既有 Qdrant / Redis，见 [`05-qdrant-rag.md`](./05-qdrant-rag.md)。

## 1. 目标

将本仓声纹能力提升至生产级，满足：

| 要求       | 说明                                                                                  |
| ---------- | ------------------------------------------------------------------------------------- |
| 开源栈     | Silero VAD + DeepFilterNet3 + 3D-Speaker（ERes2Net-Large）+ Qdrant + Redis + Postgres |
| 高精度     | 完整预处理 → VAD → AI 降噪 → Embedding → 校准分数 → 动态阈值                          |
| 1:1 核验   | 已知 `profile_id` 的身份验证（桌面助手门禁主路径）                                    |
| 1:N 识别   | 未知说话人在库内 Top-K 身份识别（会议 / 客服 / 多用户场景）                           |
| Agent 场景 | 智能助手录音门禁、多说话人筛选、后续可扩展到会议纪要说话人标注                        |

成功标准：

1. 同人短语音（≥2s 有效语音）在办公噪声下 1:1 门禁可用；异人拒识稳定。
2. 库规模至数千人 × 每人数段模板时，1:N 识别延迟可控（P95 目标见 §12）。
3. 录入 / 核验 / 识别 / 删除全链路状态闭合；换模型必须全量重录（无旧模板共存）。

## 2. 非目标

- 唤醒词（Wake Word）
- ASR / 纠错算法改造（声纹不参与转写与纠错）
- 与旧版 ECAPA / ERes2NetV2-192 / 单向量均值模板的**任何兼容或迁移**
- 独立 K8s 微服务拆分（本期仍落在 `platform-agent-service` 进程内模块化；接口与模块边界按可拆分设计）
- 平台达梦存储声纹（仅 Agent Postgres + Qdrant）
- 高安全活体检测一期必做（ASVspoof 列为二期可选）

## 3. 破坏性收敛原则（不做兼容）

本期为**替换式落地**，禁止双轨：

| 项       | 旧实现                                             | 新实现                               | 处理                                     |
| -------- | -------------------------------------------------- | ------------------------------------ | ---------------------------------------- |
| 模型     | FunASR `ERes2NetV2` 192 维                         | 3D-Speaker **ERes2Net-Large** 512 维 | 直接切换；旧 `model_id` / 旧维度一律废弃 |
| 模板形态 | 单条 JSONB embedding + 在线均值 `merge_embeddings` | **每用户多段独立 embedding**（3~5）  | 重建表结构与 Qdrant collection           |
| 检索     | Postgres 取一条向量 + 内存 Cosine                  | Qdrant ANN Top-K + Cosine 精排       | 删除「只读 PG 向量比对」路径             |
| API      | 仅 `verify(profile_id)`                            | `verify`（1:1）+ `identify`（1:N）   | 契约按新形状重写；无旧字段别名           |
| 前端门禁 | 选用户 + 周期 verify                               | 同流程，但分数语义改为校准分         | 无 `needs_reenroll` 迁移提示依赖旧数据   |

上线动作：**清空** `agent_voiceprints` 与声纹 Qdrant collection，要求所有用户重新录入。不提供自动重算 / 双读。

## 4. 现状差距（对照）

| 能力      | 当前（POC）                          | 生产目标                                                            |
| --------- | ------------------------------------ | ------------------------------------------------------------------- |
| 预处理    | PCM 解析 + 能量门限；浏览器自带 NS   | 重采样 16k → 响度归一 → 去直流 → 高通 → Silero VAD → DeepFilterNet3 |
| Embedding | ERes2NetV2 192d，临时 WAV 文件推理   | ERes2Net-Large 512d，内存波形推理（避免反复落盘）                   |
| 录入      | 单次约 4.5s，多次则均值合并为 1 向量 | 强制 3~5 段独立模板，引导不同环境/设备                              |
| 1:1       | 有（固定阈值 0.65）                  | Cosine → S-Norm / Logistic 校准 → 场景阈值                          |
| 1:N       | 无                                   | Qdrant Top-K → 精排 → Unknown                                       |
| 缓存      | 无声纹缓存                           | Redis 热用户 embedding 缓存                                         |
| 存储      | PG `embedding JSONB` 单向量          | PG 存用户元数据 + 样本元信息；向量只在 Qdrant                       |
| 观测      | 几乎无                               | 各阶段耗时、分数、模型版本、FAR/FRR 抽样                            |

当前关键实现（将被本方案替换）：

| 层   | 路径                                                                        |
| ---- | --------------------------------------------------------------------------- |
| 特征 | `app/services/voice/voiceprint_features.py`                                 |
| 业务 | `app/services/voice/voiceprint_service.py`                                  |
| 存储 | `app/services/voice/voiceprint_store.py` + `agent_voiceprints`              |
| API  | `app/api/voiceprints.py`、`main.py` 路由                                    |
| 桌面 | `VoiceInput.tsx` 门禁、`VoiceprintManagerModal.tsx` 录入、`AgentController` |

## 5. 总体架构（落入本仓）

声纹仍挂在 **Agent `:8008`**，与 ASR 并列的「语音前处理」能力；不经 Platform MCP，不经父图。

```text
桌面 Electron（麦克风 PCM 16k/16bit/mono）
        │
        │  enroll / verify / identify  (multipart PCM)
        ▼
┌───────────────────────────────────────────────────────────┐
│              platform-agent-service (:8008)                 │
│                                                           │
│  api/voiceprints  →  voiceprint_service                   │
│                           │                               │
│           ┌───────────────┼───────────────┐               │
│           ▼               ▼               ▼               │
│     preprocess      embedding_engine   decision           │
│   (VAD+DFNet3)     (ERes2Net-Large)   (calibrate+thr)     │
│           │               │               │               │
│           └───────┬───────┘               │               │
│                   ▼                       │               │
│            Redis 热缓存 ◄─────────────────┘               │
│                   │                                       │
│                   ▼                                       │
│         Qdrant collection: agent_voiceprints              │
│                   │                                       │
│                   ▼                                       │
│         Postgres: agent_voiceprint_profiles               │
│                   + agent_voiceprint_samples（元数据）     │
└───────────────────────────────────────────────────────────┘
```

与 ASR 的关系（保持解耦）：

```text
麦克风
  →【声纹门禁】verify(selected_profile) 不通过则不上行
  → Agent WS Realtime ASR → 按段纠错 → 输入框 → 用户发送 chat
```

说明：门禁仍在桌面侧调用 Agent HTTP；ASR 走既有 WS。声纹服务端不消费 ASR 音频流（一期不做服务端旁路核验）。

## 6. 技术选型（本仓定稿）

| 模块         | 选型                                                                                     | 本仓理由                                 |
| ------------ | ---------------------------------------------------------------------------------------- | ---------------------------------------- |
| 采集         | 桌面 WebAudio → PCM16 mono 16kHz                                                         | 已有 `VoiceInput` / 录入面板模式         |
| 预处理       | 服务端统一管线（§7）                                                                     | 避免浏览器 NS 与服务端特征不一致         |
| VAD          | **Silero VAD**                                                                           | 开源效果领先；切有效语音段               |
| 降噪         | **DeepFilterNet3**（可选；与主依赖 numpy 冲突时默认关闭，惰性加载）                      | 复杂噪声优于 RNNoise；嵌入前执行         |
| 声纹模型     | **3D-Speaker ERes2Net-Large**（512 维）                                                  | 替换 FunASR V2-192；中文与短语音表现更强 |
| 推理封装     | `modelscope` / `3D-Speaker` 官方推理路径（或 FunASR 同系 Large 权重，**唯一 model_id**） | 进程内单例 + device=cpu/cuda             |
| 向量库       | **Qdrant**（新建独立 collection）                                                        | 仓内已部署；中小规模足够；不引入 Milvus  |
| 热缓存       | **Redis**                                                                                | 已有 `REDIS_URL`；缓存 profile 热向量    |
| 用户元数据   | **Agent Postgres**                                                                       | 达梦禁止写；与会话库同实例               |
| 相似度       | Cosine（向量均 L2 归一化后等价点积）                                                     | 与业界一致                               |
| 分数校准     | S-Norm + Logistic Calibration                                                            | 使 score≈可信度                          |
| 活体（二期） | ASVspoof baseline                                                                        | 高安全场景可选                           |

**不采用**：Milvus（运维成本）、FAISS 单机主路径（多进程 Agent 难共享）、浏览器降噪作为唯一 NS、单向量均值模板。

推荐默认权重（实现时以官方仓库当日 ID 为准，写入配置）：

```text
VOICEPRINT_MODEL_ID=<3D-Speaker ERes2Net-Large 官方 model id>
VOICEPRINT_EMBEDDING_DIM=512
```

## 7. 音频预处理管线

所有 enroll / verify / identify 共用同一管线，保证训练分布与推理分布一致。

```text
PCM/WAV bytes
  → ① 解析为 float32 mono
  → ② Resample → 16 kHz
  → ③ 去直流（减均值）
  → ④ 高通滤波（如 80Hz Butterworth）
  → ⑤ Loudness normalize（目标响度，避免削波）
  → ⑥ Silero VAD：切出有效语音；丢弃过短片段
  → ⑦ DeepFilterNet3：对有效段降噪
  → ⑧ 拼接 / 截断至模型输入窗口（录入建议有效语音 ≥8s/段；核验 ≥2s）
  → Embedding
```

失败语义（显式错误，不静默通过）：

| 条件                            | 错误                              |
| ------------------------------- | --------------------------------- |
| 总时长过短 / VAD 后有效语音不足 | `audio_too_short`                 |
| 能量过低                        | `audio_energy_low`                |
| 降噪或模型加载失败              | `pipeline_failed`（日志含阶段名） |

## 8. 数据模型

### 8.1 Postgres（元数据，不含向量本体）

替换原 `agent_voiceprints` 单表单向量结构：

```sql
-- 用户档案
CREATE TABLE agent_voiceprint_profiles (
    id           TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    description  TEXT NOT NULL DEFAULT '',
    model_id     TEXT NOT NULL DEFAULT '',
    sample_count INT  NOT NULL DEFAULT 0,
    status       TEXT NOT NULL DEFAULT 'pending',  -- pending | enrolled | disabled
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 每段录入样本元数据（向量在 Qdrant，point_id = sample.id）
CREATE TABLE agent_voiceprint_samples (
    id           TEXT PRIMARY KEY,
    profile_id   TEXT NOT NULL REFERENCES agent_voiceprint_profiles(id) ON DELETE CASCADE,
    model_id     TEXT NOT NULL,
    duration_ms  INT  NOT NULL DEFAULT 0,
    device_hint  TEXT NOT NULL DEFAULT '',   -- headset | laptop | phone | meeting | other
    env_hint     TEXT NOT NULL DEFAULT '',   -- office | home | outdoor | other
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_voiceprint_samples_profile
    ON agent_voiceprint_samples (profile_id);
```

上线迁移策略（破坏性）：

1. `DROP TABLE IF EXISTS agent_voiceprints;`
2. 创建上表；
3. 重建 Qdrant collection（见下）。

### 8.2 Qdrant collection

| 项       | 值                                                                                |
| -------- | --------------------------------------------------------------------------------- |
| 名称     | `agent_voiceprints`（配置项，与知识库 collection 隔离）                           |
| 向量维度 | **512**                                                                           |
| 距离     | Cosine                                                                            |
| point id | `sample.id`（UUID hex）                                                           |
| payload  | `profile_id`, `display_name`, `model_id`, `device_hint`, `env_hint`, `created_at` |

删除用户：删 PG profile（CASCADE samples）+ Qdrant 按 `profile_id` filter delete。  
删除单样本：删 sample 行 + delete point；若 `sample_count` 低于最低录入数则 `status=pending`。

### 8.3 Redis 缓存

| Key                    | Value                                                            | TTL             |
| ---------------------- | ---------------------------------------------------------------- | --------------- |
| `vp:emb:{profile_id}`  | JSON 数组：该用户当前全部 sample embedding（或 Qdrant 拉取结果） | 可配置，默认 1h |
| `vp:meta:{profile_id}` | `display_name`, `sample_count`, `model_id`                       | 同 TTL          |

录入 / 删除 / 禁用时 **主动 invalidate**。1:1 优先读缓存；未命中再 Qdrant scroll/retrieve by profile。

## 9. 业务流程

### 9.1 录入（Enrollment）

生产要求：**最少 3 段、最多 5 段**；每段有效语音建议 **8~10s**（VAD 后）。

```text
创建 profile (status=pending)
  → 第 1 段录音 → preprocess → embedding → 写 sample + Qdrant upsert
  → 第 2 段 …
  → 第 3 段 …  （达到 VOICEPRINT_ENROLL_MIN_SAMPLES）
  → status=enrolled，invalidate Redis
```

桌面录入 UX：

- 向导式多段录入（进度 1/3、2/3、3/3）；
- 每段可标注 `device_hint` / `env_hint`（可选下拉）；
- 未达最少段数：`enrolled=false`，不可用于门禁；
- **追加录入**：在已 enrolled 基础上继续加段直至上限；超过上限拒绝或要求先删旧段（实现选「拒绝并提示删除」）。

禁止：把多段均值合成单一向量。决策时对多模板取 **max cosine**（或 Top-M 平均，配置二选一，默认 **max**）。

### 9.2 1:1 核验（Verify）— 助手门禁主路径

```text
输入: profile_id + PCM
  → preprocess + embedding
  → 取该 profile 全部模板（Redis → 否则 Qdrant filter profile_id）
  → score_raw = max cosine(probe, templates)
  → score = calibrate(score_raw, context)
  → matched = score >= threshold(scene)
  → 返回 matched, score, threshold, profile_id, display_name, model_id, latency_ms
```

桌面：`VoiceInput` 选中用户后周期性 verify；不匹配则不上行 ASR（与 `10` §7 一致）。  
唯一开关 **`VOICEPRINT_ENABLED`**：桌面经 `GET /api/agent/voiceprints/config` 同步；关闭时不强制选人、不调用 verify；服务端 verify 若仍被调用则返回 `skipped` + `reason=voiceprint_disabled`。

### 9.3 1:N 识别（Identify）

```text
输入: PCM（无 profile_id）
  → preprocess + embedding
  → Qdrant search Top-K（默认 K=20）
  → 按 profile 聚合（同一用户多 point 取 max）
  → 取最高分用户 → calibrate → 与阈值比较
  → 高于阈值: { profile_id, display_name, score }
  → 否则: { profile_id: null, decision: "unknown", score }
```

用例：未预选用户的会议室设备、客服进线识别、后续多说话人扩展入口。

### 9.4 分数校准与阈值

**校准（一期必做最小集）**：

1. 对 Cosine 原始分做 **Logistic** 映射到 `[0,1]`（参数来自配置或离线拟合文件）；
2. 有 cohort 时启用 **S-Norm**（用一组非目标说话人分数做标准化）；无 cohort 时可仅 Logistic。

**阈值**：

| 场景 `scene`     | 默认阈值（可配）       | 用途                   |
| ---------------- | ---------------------- | ---------------------- |
| `assistant_gate` | 较高（如 0.83 校准分） | 桌面门禁，偏保守降 FAR |
| `meeting`        | 更高                   | 嘈杂环境               |
| `identify_open`  | 中等                   | 1:N 开放集             |

禁止写死「Cosine 0.65 恒等于可信」。配置项示例：

```bash
VOICEPRINT_THRESHOLD_ASSISTANT_GATE=0.83
VOICEPRINT_THRESHOLD_MEETING=0.87
VOICEPRINT_THRESHOLD_IDENTIFY=0.80
VOICEPRINT_CALIBRATION_PATH=./data/voiceprint_calibration.json
```

FAR/FRR 监控数据落日志/指标，供后续调参；一期不做在线自动改阈值写库。

## 10. API 契约（替换）

统一响应：`{ code, data, message }`。

| 方法   | 路径                                              | 说明                                                            |
| ------ | ------------------------------------------------- | --------------------------------------------------------------- |
| GET    | `/api/agent/voiceprints`                          | 列表（含 `sample_count`, `status`, `enrolled`）                 |
| POST   | `/api/agent/voiceprints`                          | 创建档案                                                        |
| PATCH  | `/api/agent/voiceprints/{id}`                     | 改名/描述/禁用                                                  |
| DELETE | `/api/agent/voiceprints/{id}`                     | 删档案 + Qdrant + 缓存                                          |
| POST   | `/api/agent/voiceprints/{id}/enroll`              | 上传一段 PCM；可选 `device_hint`/`env_hint`                     |
| DELETE | `/api/agent/voiceprints/{id}/samples/{sample_id}` | 删除单段模板                                                    |
| POST   | `/api/agent/voiceprints/verify`                   | 1:1；表单：`profile_id` + `file` + `sample_rate` + 可选 `scene` |
| POST   | `/api/agent/voiceprints/identify`                 | 1:N；表单：`file` + `sample_rate` + 可选 `scene`、`top_k`       |

`verify` / `identify` 的 `data` 最小字段：

```json
{
  "matched": true,
  "decision": "accept",
  "score": 0.91,
  "score_raw": 0.72,
  "threshold": 0.83,
  "profile_id": "...",
  "display_name": "张三",
  "model_id": "...",
  "latency_ms": {
    "preprocess": 12,
    "embedding": 45,
    "search": 8,
    "total": 70
  }
}
```

`identify` 未命中时：`matched=false`, `decision="unknown"`, `profile_id=null`。

**删除的旧语义**：`needs_reenroll`、单向量 `embedding` 对外暴露、均值合并 `sample_count` 无样本列表等，均不再出现。

## 11. 模块划分（Agent 内）

建议目录（实现时按此收敛，替换旧三文件职责）：

```text
app/services/voice/voiceprint/
  __init__.py
  preprocess.py      # 重采样/滤波/归一化 + Silero + DeepFilterNet3
  embedding.py       # ERes2Net-Large 单例推理
  calibrate.py       # S-Norm / Logistic
  decision.py        # 阈值与 accept/unknown
  store_pg.py        # profiles / samples
  store_qdrant.py    # upsert / search / delete
  cache_redis.py     # 热缓存
  service.py         # enroll / verify / identify / CRUD
  metrics.py         # 结构化日志与计时
```

API 层仍：`app/api/voiceprints.py`。  
桌面：录入向导改多段；`AgentController` 增 `identifyVoiceprint`；门禁继续 `verify`。

依赖原则：

- 优先复用仓内已有 `infrastructure/redis`、`infrastructure/vector`；
- DeepFilterNet3 / Silero / 3D-Speaker 为声纹专用依赖，按需惰性加载；
- **禁止** Agent `import platform_mcp`；声纹不进 catalog。

## 12. 性能与硬件

| 指标                               | 目标（单实例，CPU 优先）             |
| ---------------------------------- | ------------------------------------ |
| 1:1 verify P95（含预处理+推理）    | ≤ 300ms（有效语音 2~3s）             |
| 1:N identify P95（库 ≤5 万 point） | ≤ 400ms                              |
| 并发                               | 桌面助手场景 ≪100；同机可与 ASR 共存 |

硬件建议沿用方案原文：中低并发 CPU 可跑；高并发再上 GPU 批量。配置 `VOICEPRINT_DEVICE=cpu|cuda`。

## 13. 可观测性

每次 verify/identify/enroll 打结构化日志（可进现有 logging）：

```text
event=voiceprint_verify
profile_id=... model_id=... scene=...
score_raw=... score=... threshold=... decision=...
ms_preprocess=... ms_embedding=... ms_search=... ms_total=...
vad_speech_ms=... top_k=...
```

健康检查：`/health` 可增加 `voiceprint` 探针（模型是否已加载、Qdrant collection 是否存在）— fail-open 与否由 `VOICEPRINT_ENABLED` 决定。

## 14. 与其它架构文档的边界

| 文档                                                         | 关系                                                                      |
| ------------------------------------------------------------ | ------------------------------------------------------------------------- |
| [`10-voice-asr.md`](./10-voice-asr.md)                       | ASR/纠错；声纹仅门禁，不参与纠错                                          |
| [`05-qdrant-rag.md`](./05-qdrant-rag.md)                     | 知识库 collection 与声纹 collection **物理隔离**；维度不同（1024 vs 512） |
| [`03-agent-runtime.md`](./03-agent-runtime.md)               | 无交叉；声纹不进 StateGraph                                               |
| [`09-platform-db-readonly.md`](./09-platform-db-readonly.md) | 声纹只写 Agent Postgres / Qdrant                                          |

## 15. 配置清单

```bash
VOICEPRINT_ENABLED=true
VOICEPRINT_MODEL_ID=<eres2net-large>
VOICEPRINT_EMBEDDING_DIM=512
VOICEPRINT_DEVICE=           # 空=自动
VOICEPRINT_ENROLL_MIN_SAMPLES=3
VOICEPRINT_ENROLL_MAX_SAMPLES=5
VOICEPRINT_ENROLL_MIN_SPEECH_MS=8000
VOICEPRINT_VERIFY_MIN_SPEECH_MS=2000
VOICEPRINT_QDRANT_COLLECTION=agent_voiceprints
VOICEPRINT_SEARCH_TOP_K=20
VOICEPRINT_SCORE_AGG=max     # max | mean_top_m
VOICEPRINT_THRESHOLD_ASSISTANT_GATE=0.83
VOICEPRINT_THRESHOLD_MEETING=0.87
VOICEPRINT_THRESHOLD_IDENTIFY=0.80
VOICEPRINT_CALIBRATION_PATH=
VOICEPRINT_REDIS_TTL_SEC=3600
VOICEPRINT_VAD_ENABLED=true
VOICEPRINT_DENOISE_ENABLED=false
```

> DeepFilterNet3 与当前主依赖 `numpy>=2` 不兼容时保持 `VOICEPRINT_DENOISE_ENABLED=false`；代码侧惰性加载，缺包则跳过降噪。

## 16. 分期实施

| 阶段           | 交付                                                                                  | 验收焦点                    |
| -------------- | ------------------------------------------------------------------------------------- | --------------------------- |
| **P0**         | 预处理骨架 + ERes2Net-Large 512 + PG/Qdrant 多模板 + verify/identify API + 破坏性清库 | 单测 mock + 手工 1:1/1:N    |
| **P1**         | Silero VAD + DeepFilterNet3 接入；桌面多段录入向导；门禁改用校准分与场景阈值          | 噪声环境门禁；录入 3 段强制 |
| **P2**         | Redis 热缓存、完整 latency 指标、校准参数文件、健康探针                               | 压测与调参                  |
| **P3（可选）** | ASVspoof 活体、独立推理进程 / GPU 批处理                                              | 高安全 / 高并发             |

## 17. 测试策略

| 类型 | 内容                                                                      |
| ---- | ------------------------------------------------------------------------- |
| 单测 | preprocess 边界、聚合 max、校准单调、Qdrant/Redis mock 下 verify/identify |
| 集成 | 真实模型标记 `@pytest.mark.integration`；清库后录入 3 段再核验            |
| 桌面 | 未选用户不可录音（门禁开）；异人过滤不上行；多段录入进度与 enrolled 状态  |
| 回归 | ASR 实时转写与纠错路径不受影响（`10` 验收仍成立）                         |

## 18. 影响面清单（实现时对照）

| 类别       | 项                                                                                                                 |
| ---------- | ------------------------------------------------------------------------------------------------------------------ |
| 直接改动   | Agent `voiceprint*`、`schema.py`、`config`、`.env.example`、`pyproject` 依赖；桌面录入/门禁/`AgentController`/i18n |
| 对称路径   | enroll 多段、删样本、删用户、verify 门禁开/关、identify 新入口；**与 chat/resume/reject 无状态耦合**               |
| 共享状态   | PG 新表、Qdrant 新 collection、Redis `vp:*`；无 checkpoint / 无 `pending_*`                                        |
| 契约       | HTTP JSON 字段替换；无 SSE/catalog 变更                                                                            |
| 非目标回滚 | 不保留 192 维与单向量均值路径                                                                                      |

## 19. 验收要点

- [ ] 旧 `agent_voiceprints` 单向量数据不可用；须重录 ≥3 段后 `enrolled=true`
- [ ] 同人 verify：`decision=accept` 且带 `score` / `latency_ms`
- [ ] 异人 verify：拒识；不上行 ASR
- [ ] identify：库内用户可识别；陌生人 `unknown`
- [ ] 换 `VOICEPRINT_MODEL_ID`：旧 Qdrant point 与库清空策略执行，无静默混用
- [ ] 知识库 Qdrant collection 与 RAG 行为无回归
- [ ] `VOICEPRINT_VAD_ENABLED` / `DENOISE_ENABLED` 关闭时管线仍可跑通（便于排障），默认生产开启

## 20. 风险与决策记录

| 风险                                     | 缓解                                                                                                          |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| DeepFilterNet3 / Silero 增大依赖与冷启动 | 惰性加载；提供关闭开关；首次请求预热接口可选                                                                  |
| ERes2Net-Large 与旧 V2 分数不可比        | 不做兼容；重新标定阈值                                                                                        |
| 桌面浏览器 NS 与服务端 DFNet 双重降噪    | 录入/核验上传**原始 PCM**；可关闭浏览器 `noiseSuppression` 以减少音色损伤（实现时桌面 getUserMedia 约束写入） |
| 多模板 max 聚合抬高异人碰撞              | 提高门禁阈值 + Top-K 次高分间隔检查（可选：`score_gap`）                                                      |

---

**结论**：在本仓复用 Redis + Qdrant + Agent Postgres，以破坏性替换方式落地「预处理 → ERes2Net-Large → 多模板向量检索 → 校准决策」主链；桌面助手继续 1:1 门禁，并新增 1:N identify，从而达到方案所述生产级声纹工程形态，而不引入旧模板兼容层。
