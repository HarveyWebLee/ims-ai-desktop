"""
应用配置：从环境变量和 .env 文件读取 Agent 服务运行参数。

文件职责
--------
集中定义 Agent 服务的「开关」与密钥：端口、Mock、Plan 确认、preflight、
StateGraph、各厂商 API Key、平台 API 地址、Postgres、Qdrant、语音转写等。
全进程通过模块级单例 ``settings`` 读取，避免各处分散硬编码。

在 Agent 流程中的位置
--------------------
  进程启动（main lifespan / uv run dev）
    → 加载本模块 Settings（.env + 环境变量）
    → chat / Plan / 工具 / checkpointer 各处 ``from app.config import settings``

如何被调用
----------
  from app.config import settings
  print(settings.port)

【配置从哪来？】
1. 环境变量（操作系统或 Docker 注入）
2. 仓根 ``.env.shared``（跨端公共项，如 PLATFORM_API_BASE）
3. platform-agent-service/.env（本服务项；同名键覆盖 shared）

【为什么用 pydantic_settings？】
Pydantic 的 BaseSettings 会自动：
  - 把环境变量名映射到类属性（不区分大小写，如 PORT → port）
  - 做类型转换（字符串 "8008" → int 8008）
  - 提供默认值
"""

from pathlib import Path

# pydantic_settings：Pydantic v2 里专门读环境变量的模块
from pydantic_settings import BaseSettings, SettingsConfigDict

# ---------------------------------------------------------------------------
# 固定 .env 路径，避免从其他工作目录启动 uvicorn 时找不到 Key
# ---------------------------------------------------------------------------

# app/config.py → parent 是 app → parent.parent 是 platform-agent-service
_SERVICE_ROOT = Path(__file__).resolve().parent.parent
_REPO_ROOT = _SERVICE_ROOT.parent.parent
_ENV_SHARED = _REPO_ROOT / ".env.shared"
_ENV_FILE = _SERVICE_ROOT / ".env"


def _env_files() -> tuple[str, ...]:
    """shared 在前、本服务在后（后者覆盖同名键）。"""
    files: list[str] = []
    if _ENV_SHARED.is_file():
        files.append(str(_ENV_SHARED))
    if _ENV_FILE.is_file():
        files.append(str(_ENV_FILE))
    return tuple(files)


class Settings(BaseSettings):
    """
    全局配置类。每个属性对应一个配置项。

    model_config 是 Pydantic v2 的写法，等价于旧版 class Config。
    """

    model_config = SettingsConfigDict(
        env_file=_env_files() or None,
        env_file_encoding="utf-8",
        extra="ignore",  # .env 里有多余字段时不报错
    )

    # HTTP 服务监听端口（可用环境变量 PORT 覆盖）
    port: int = 8009

    # 意图识别 AI 优先：true=classify 恒路由 react；false=原 chat_direct/device_gate/plan_confirm 门控
    agent_intent_ai_first: bool = True

    # Phase C2：多步规则 Plan 执行前需用户确认（plan_confirm HITL）
    agent_plan_confirm_enabled: bool = True

    # Phase C2+：仅含写操作/高风险步骤的多步 Plan 需 plan_confirm；纯查询类多步可跳过
    agent_plan_confirm_write_only: bool = True

    # Phase C3：工具 invoke 前统一 preflight（缺参 → ask_params，避免 API 500）
    agent_preflight_enabled: bool = True

    # Phase D1：多步 Plan 优先用 LLM 显式生成（失败回退规则 build_task_plan）
    agent_llm_plan_enabled: bool = True

    # D1 Plan 参数：默认仅用规则 infer_plan_params，避免 qwen structured 阻塞 plan_confirm SSE
    agent_llm_plan_params_enabled: bool = False

    # D1 Plan / 参数 structured output 单次调用超时（秒）；仅启用 LLM 抽参/规划时生效
    agent_llm_plan_timeout_seconds: float = 30.0

    # ReAct 流式：worker 长时间无 SSE 事件则中断并向前端推送 error（避免侧栏空白挂起）
    agent_stream_idle_timeout_seconds: float = 120.0

    # Phase P1：BPMN 条件分支图执行（BpmnExecutor）；默认关闭便于灰度
    agent_bpmn_condition_exec: bool = False

    # Phase P2：NL → Flow IR → FlowDocument 编译；须同时开启 condition_exec 才端到端生效
    agent_bpmn_llm_compile: bool = False

    # 各厂商 API Key（留空字符串表示未配置）
    deepseek_api_key: str = ""
    dashscope_api_key: str = ""

    # 综合信息平台后端 API 根地址（Agent 调告警等 Server Tool 时用）
    platform_api_base: str = "http://127.0.0.1:18001/api/app"

    # 共享 JSON / 平台 API 索引目录（contracts.platform_api_catalog 等）
    agent_data_dir: str = str((_SERVICE_ROOT / "app" / "data").resolve())
    agent_service_root: str = str(_SERVICE_ROOT.resolve())

    # 语音转写（DashScope qwen3-asr-flash）
    transcribe_model: str = "qwen3-asr-flash"
    transcribe_max_bytes: int = 10 * 1024 * 1024  # 10MB
    transcribe_timeout_seconds: float = 120.0
    # 转写后多级纠错：Rule → Redis Cache → Dictionary → Vector → LLM
    transcribe_rag_enabled: bool = True
    transcribe_dictionary_enabled: bool = True
    transcribe_dictionary_path: str = ""
    transcribe_rag_top_k: int = 2
    # 纠错用聊天模型（catalog modelId）；默认 flash 以控制延迟
    transcribe_correct_model: str = "qwen3.5-flash-2026-02-23"
    # 纠错超时宜短：超时直接回退 ASR 原文，避免拖慢侧栏
    transcribe_correct_timeout_seconds: float = 6.0
    # 相似度低于此值的命中不进入纠错（减少无效 LLM）
    transcribe_correct_min_score: float = 0.42
    # 注入纠错 Prompt 的单条片段最大字符数
    transcribe_correct_snippet_chars: int = 160
    # 纠错模型输出上限（越短越快）
    transcribe_correct_max_tokens: int = 48
    # Redis 纠错映射 TTL（秒）
    transcribe_correct_cache_ttl_seconds: int = 30 * 24 * 3600
    # 声纹门禁：语音输入前须选择已录入用户，并比对通过后才接受 ASR
    # 嵌入后端为 FunASR ERes2NetV2（192 维）；换 model_id 后须重新录入
    # 临时默认关闭声纹门禁；与桌面端 VOICEPRINT_GATE_ENABLED 对齐后再开启
    voiceprint_enabled: bool = False
    # ERes2Net 余弦常见同人 0.5~0.9、异人更低；门禁开启后建议 ≥0.65
    voiceprint_match_threshold: float = 0.65
    voiceprint_model_id: str = "iic/speech_eres2netv2_sv_zh-cn_16k-common"
    # 空=自动（有 CUDA 用 cuda，否则 cpu）
    voiceprint_device: str = ""
    # 流式分片并行：线程池大小 / 会话 TTL / finish 等待上限
    transcribe_stream_enabled: bool = True
    transcribe_pipeline_workers: int = 4
    transcribe_stream_session_ttl_seconds: int = 600
    transcribe_stream_finalize_wait_seconds: float = 12.0
    # Realtime ASR（词级 partial；北京地域默认）
    transcribe_realtime_enabled: bool = True
    transcribe_realtime_model: str = "qwen3-asr-flash-realtime"
    transcribe_realtime_ws_url: str = "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"
    transcribe_realtime_sample_rate: int = 16000

    # Postgres（会话/审计表 + AsyncPostgresSaver；宿主机 16543 → 容器 5432）
    # 留空则回退 InMemorySaver（重启后会话丢失）
    postgres_dsn: str = ""

    # Redis（语音纠错 Cache 等；宿主机 13386 → 容器 6379）
    # 留空则禁用 Redis 能力；健康检查标记 disabled，业务侧 fail-open
    redis_url: str = "redis://127.0.0.1:13386/0"

    # Platform MCP Server（双层 MCP）
    platform_mcp_url: str = "http://127.0.0.1:8010/mcp"
    # true：Platform MCP 不可达时启动预热失败直接退出；false 仅允许进程起来（仍不绑 raw）
    agent_mcp_required: bool = True
    # 额外 MCP 服务器 JSON，例：
    # {"filesystem":{"transport":"stdio","command":"npx","args":["-y","@modelcontextprotocol/server-filesystem","/tmp"]}}
    agent_mcp_extra_servers_json: str = ""
    # Agent MCP Gateway 共享密钥；可与 Bearer JWT 二选一。空=不接受密钥头，仍须 Bearer
    agent_mcp_gateway_key: str = ""
    # 启动时预热 Platform MCP 工具列表
    agent_mcp_warmup_on_start: bool = True
    # MCP 工具列表缓存 TTL（秒）；0=仅手动 clear / 进程重启才刷新
    agent_mcp_cache_ttl_seconds: int = 300
    # catalog.required_permissions：JWT 未声明 permissions 时是否拒绝写工具（默认 true）
    agent_tool_permission_fail_closed: bool = True

    # Qdrant 向量库（docker compose 默认映射宿主机 16333 → 容器 6333）
    # 留空则禁用向量能力；健康检查与入库脚本会跳过/报错
    qdrant_url: str = "http://127.0.0.1:16333"
    qdrant_api_key: str = ""
    qdrant_collection: str = "platform_knowledge"
    # 与 embedding 模型维度一致（DashScope qwen3.7-text-embedding 默认 1024）
    qdrant_vector_size: int = 1024
    # OpenAI 兼容 Embedding（默认走 DashScope compatible-mode）
    embedding_model: str = "qwen3.7-text-embedding"
    embedding_provider: str = "dashscope"
    # 文本切块：字符数 / 重叠，入库脚本与 VectorStore 共用
    vector_chunk_size: int = 800
    vector_chunk_overlap: int = 120
    # 单次 upsert 点数上限，避免 Qdrant HTTP JSON 超过 32MB
    vector_upsert_batch_size: int = 64
    # 每轮被动 RAG 注入条数
    rag_top_k: int = 4

    # 知识库：图片视觉抽取（DashScope VL → 文本 → Embedding）
    knowledge_vision_enabled: bool = True
    knowledge_vision_model: str = "qwen-vl-plus"
    knowledge_vision_timeout_seconds: float = 120.0
    knowledge_vision_max_side: int = 1280
    knowledge_image_max_bytes: int = 8 * 1024 * 1024
    # 表格入库最大行数（单 sheet / 单 csv），防止超大表撑爆上下文
    knowledge_table_max_rows: int = 2000

    # 平台业务达梦（智能化侧只读；见 docs/architecture/09-platform-db-readonly.md）
    dm_host: str = ""
    dm_port: int = 5236
    dm_user: str = ""
    dm_password: str = ""
    dm_schema: str = ""
    # 必须为 true；为 false 时拒绝发起同步
    dm_read_only: bool = True
    # 可选：DmJdbcDriver18.jar 绝对路径（无 dmPython 时走 JayDeBeApi）
    dm_jdbc_jar: str = ""

    # 实体表 → 向量：空=不转换；*=全部表；逗号分隔表名
    entity_sync_tables: str = ""
    entity_sync_max_rows_per_table: int = 5000
    qdrant_collection_entities: str = "platform_entities"

    # 开发排查：输出 [AgentTrace] 结构化日志（跨轮次 HITL / Plan 污染定位）
    # 环境变量 AGENT_DEBUG_TRACE=true 开启；uv run dev 默认会 setdefault 为 true
    agent_debug_trace: bool = False


# 模块级单例：整个进程共用一份 settings（别处 from app.config import settings）
settings = Settings()

# 将 Agent 能力注入 contracts（禁止 contracts 反向 import app）
from app.contracts_runtime import wire_contracts_runtime  # noqa: E402

wire_contracts_runtime()
