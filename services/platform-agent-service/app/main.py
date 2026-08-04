"""
FastAPI 应用入口：注册路由、中间件、生命周期钩子。

【本文件在架构中的位置】
  浏览器 / 前端 App
       ↓ HTTP
  app/main.py（本文件）— 路由分发
       ↓
  app/api/*.py — 具体接口（chat、sessions、transcribe…）
       ↓
  app/application/conversation + execution — Agent 对话与执行

【常用命令】
  uv run dev          # 推荐：热重载开发
  curl localhost:8009/health  # 健康检查（默认端口，可用 .env PORT 覆盖）
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated  # 给参数加「元数据」，如 File()、Form()

# FastAPI：现代 Python Web 框架；UploadFile 处理文件上传
from fastapi import FastAPI, File, Form, Header, Request, UploadFile, WebSocket
from fastapi.middleware.cors import CORSMiddleware  # 跨域中间件

# 各 API 子模块（具体实现在 app/api/ 下）
from app.api import chat, models, resume, sessions, transcribe
from app.api.bpmn import (
    BpmnConvertRequest,
    BpmnSnapshotSaveRequest,
    BpmnValidateRequest,
)
from app.api.entities import EntitySearchBody
from app.api.entity_sync import EntitySyncRequest
from app.api.knowledge import KnowledgeDeleteBody, KnowledgeExportBody, KnowledgeSearchBody
from app.api.voiceprints import VoiceprintCreateBody, VoiceprintUpdateBody
from app.config import settings
from app.models.router import has_real_model_credentials
from app.persistence import close_persistence, init_persistence
from app.persistence.bootstrap import is_postgres_enabled

# 模块级 logger，日志名一般为 app.main
logger = logging.getLogger(__name__)

_SERVICE_ROOT = Path(__file__).resolve().parent.parent
# 健康检查 build_id：部署后 curl /health 可确认是否命中当前代码版本
_BUILD_ID = "2026-07-23-phase-a-bpmn-obs-v1"

# 启动时 init_persistence 的返回值缓存在此，供 /health 展示
_persistence_info: dict = {}

# Gateway FastMCP ASGI 须先于 FastAPI 创建，以便合并 lifespan（Streamable HTTP 会话管理）
from app.mcp.gateway import create_gateway_http_app  # noqa: E402

_gateway_http_app = create_gateway_http_app()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """合并 Gateway FastMCP lifespan、persistence、MCP warmup。"""
    global _persistence_info

    async with _gateway_http_app.lifespan(_app):
        _persistence_info = await init_persistence(settings.postgres_dsn)
        from app.utils.logging_setup import configure_agent_logging

        configure_agent_logging(debug_trace=settings.agent_debug_trace)
        logger.info(
            "Agent 服务启动: port=%s build_id=%s persistence=%s has_api_key=%s mcp_required=%s",
            settings.port,
            _BUILD_ID,
            _persistence_info.get("mode"),
            has_real_model_credentials(),
            settings.agent_mcp_required,
        )
        if settings.agent_debug_trace:
            logger.info(
                "[AgentTrace] 排查日志已开启；chat/resume 时将输出 orchestration 快照与路径分支"
            )
        if settings.agent_mcp_warmup_on_start:
            from app.mcp.client import warmup_mcp_tools

            try:
                status = await warmup_mcp_tools()
                if status.get("ok"):
                    logger.info(
                        "MCP warmup: ok=%s tools=%s",
                        status.get("ok"),
                        status.get("tool_count"),
                    )
                else:
                    logger.warning(
                        "MCP warmup 未成功（Agent 仍启动）: %s；"
                        "请先启动 Platform MCP :8010，或将 AGENT_MCP_REQUIRED=true 改为启动失败退出",
                        status.get("error") or "unknown",
                    )
            except Exception as exc:  # noqa: BLE001
                # agent_mcp_required=true 时 warmup 内部会再抛；此处兜底
                logger.error("MCP warmup 失败且 AGENT_MCP_REQUIRED=true，拒绝启动: %s", exc)
                raise
        if settings.agent_playbook_enabled and settings.agent_playbook_watch:
            from app.services.playbook.watcher import start_playbook_watcher

            try:
                await start_playbook_watcher()
            except Exception:  # noqa: BLE001
                logger.exception("playbook watcher 启动失败（Agent 仍继续）")
        try:
            yield
        finally:
            from app.infrastructure.redis.client import close_redis_client
            from app.infrastructure.vector.client import close_qdrant_client
            from app.services.playbook.watcher import stop_playbook_watcher

            await stop_playbook_watcher()
            close_qdrant_client()
            close_redis_client()
            await close_persistence()


# 创建 FastAPI 应用实例；uvicorn 加载的就是这个 app 变量
app = FastAPI(
    title="platform-agent-service",
    description="综合信息平台 AI Agent 后端",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS：允许前端（不同端口）调用 API；开发环境 allow_origins=["*"] 较宽松
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """
    健康检查接口（GET，无请求体）。

    返回 JSON，含 API Key 是否配置、持久化模式、Qdrant / Platform MCP 状态等。
    """
    from app.infrastructure.redis.client import probe_redis
    from app.infrastructure.vector.client import probe_qdrant
    from app.mcp.client import probe_platform_mcp
    from app.services.voice.voiceprint import probe_voiceprint

    qdrant = probe_qdrant()
    redis_info = probe_redis()
    platform_mcp = await probe_platform_mcp()
    mcp_ok = bool(platform_mcp.get("ok")) if isinstance(platform_mcp, dict) else False
    return {
        # 进程可服务即为 ok/degraded；MCP 未就绪标 degraded，不阻止启动（见 AGENT_MCP_REQUIRED）
        "status": "ok" if mcp_ok else "degraded",
        "build_id": _BUILD_ID,
        "architecture": "mcp-dual-layer-v2",
        "service_root": str(_SERVICE_ROOT),
        "port": settings.port,
        "platform_mcp_url": settings.platform_mcp_url,
        "platform_mcp": platform_mcp,
        "agent_mcp_required": settings.agent_mcp_required,
        "agent_mcp_gateway": {
            "streamable_http": "/mcp",
            "rest_health": "/api/agent/gateway/health",
            "auth_required": True,
            "gateway_key_configured": bool((settings.agent_mcp_gateway_key or "").strip()),
        },
        "agent_tool_permission_fail_closed": settings.agent_tool_permission_fail_closed,
        "has_api_key": has_real_model_credentials(),
        "persistence": _persistence_info.get("mode", "unknown"),
        "postgres_enabled": is_postgres_enabled(),
        "qdrant": qdrant,
        "redis": redis_info,
        "voiceprint": probe_voiceprint(),
        "rag_top_k": settings.rag_top_k,
        # BPMN 灰度开关（本地联调 curl /health 可确认是否命中）
        "feature_flags": {
            "agent_intent_ai_first": settings.agent_intent_ai_first,
            "agent_bpmn_condition_exec": settings.agent_bpmn_condition_exec,
            "agent_bpmn_llm_compile": settings.agent_bpmn_llm_compile,
        },
        "observability": {
            "audit_backend": (
                "postgres" if _persistence_info.get("mode") == "postgres" else "memory"
            ),
        },
    }


@app.get("/api/agent/audit")
async def get_audit(
    thread_id: str,
    limit: int = 100,
    run_id: str | None = None,
    event_type: str | None = None,
    authorization: str | None = Header(default=None),
):
    """
    查询某会话的审计日志。

    延迟 import：只有请求进来时才加载 audit 模块，加快冷启动。
    """
    from app.api import audit as audit_api

    return await audit_api.list_thread_audit(
        thread_id,
        limit=limit,
        run_id=run_id,
        event_type=event_type,
        authorization=authorization,
    )


@app.get("/api/agent/graph/topology")
async def get_agent_graph_topology():
    """Phase D3：Agent 编排拓扑（静态 Mermaid + 节点边，供 Trace 可视化对齐）。"""
    from app.graph.parent_graph import get_agent_topology

    return {"code": 0, "data": get_agent_topology(), "message": "ok"}


@app.get("/api/agent/threads/{thread_id}/trace")
async def get_thread_trace(
    thread_id: str,
    run_id: str | None = None,
    authorization: str | None = Header(default=None),
):
    """查询 Phase 3 执行 Trace（Plan、工具调用等结构化记录）。"""
    from app.api import trace as trace_api

    return await trace_api.get_thread_trace(thread_id, run_id=run_id, authorization=authorization)


@app.get("/api/agent/models")
async def get_models():
    """返回可用 LLM 模型列表（来自 catalog.json）。"""
    return await models.list_models()


@app.get("/api/agent/sessions")
async def get_sessions(authorization: str | None = Header(default=None)):
    """列出当前用户的 Agent 会话（thread）摘要。"""
    return await sessions.list_sessions(authorization)


@app.delete("/api/agent/sessions/{thread_id}")
async def delete_session_route(
    thread_id: str,
    authorization: str | None = Header(default=None),
):
    """删除一条历史会话，并清理会话索引、pending、BPMN 与 checkpoint。"""
    return await sessions.delete_session(thread_id, authorization)


@app.get("/api/agent/threads/{thread_id}/state")
async def get_thread_state(
    thread_id: str,
    authorization: str | None = Header(default=None),
):
    """获取单个 thread 的消息历史与状态（供前端恢复侧栏）。"""
    return await sessions.get_thread_state(thread_id, authorization)


@app.post("/api/agent/bpmn/convert")
async def post_bpmn_convert(
    body: BpmnConvertRequest,
    authorization: str | None = Header(default=None),
):
    """BPMN 画布 JSON 与 Plan 步骤互转。"""
    from app.api import bpmn as bpmn_api

    return await bpmn_api.convert_bpmn(body, authorization)


@app.post("/api/agent/bpmn/validate")
async def post_bpmn_validate(
    body: BpmnValidateRequest,
    authorization: str | None = Header(default=None),
):
    """校验 BPMN 画布 JSON 结构。"""
    from app.api import bpmn as bpmn_api

    return await bpmn_api.validate_bpmn(body, authorization)


@app.get("/api/agent/threads/{thread_id}/bpmn")
async def get_thread_bpmn(
    thread_id: str,
    authorization: str | None = Header(default=None),
):
    """读取线程 BPMN 编排快照。"""
    from app.api import bpmn as bpmn_api

    return await bpmn_api.get_thread_bpmn(thread_id, authorization)


@app.put("/api/agent/threads/{thread_id}/bpmn")
async def put_thread_bpmn(
    thread_id: str,
    body: BpmnSnapshotSaveRequest,
    authorization: str | None = Header(default=None),
):
    """保存线程 BPMN 编排快照（编排草稿）。"""
    from app.api import bpmn as bpmn_api

    return await bpmn_api.save_thread_bpmn(thread_id, body, authorization)


@app.post("/api/agent/entity-sync")
async def post_entity_sync(
    body: EntitySyncRequest = EntitySyncRequest(),
    authorization: str | None = Header(default=None),
):
    """
    按 ENTITY_SYNC_TABLES（或 body.tables 覆盖）将达梦表只读同步到 Qdrant。

    空配置不转换；*=全部表；逗号分隔指定表；缺表则提示，存在的仍转换。
    """
    from app.api import entity_sync as entity_sync_api

    return await entity_sync_api.trigger_entity_sync(body, authorization)


@app.get("/api/agent/entity-sync/status")
async def get_entity_sync_status(authorization: str | None = Header(default=None)):
    """最近一次实体同步结果（进程内）与是否进行中。"""
    from app.api import entity_sync as entity_sync_api

    return await entity_sync_api.entity_sync_status(authorization)


@app.get("/api/agent/entities/stats")
async def get_entity_stats(authorization: str | None = Header(default=None)):
    """实体术语库统计（Qdrant platform_entities）。"""
    from app.api import entities as entities_api

    return await entities_api.entity_stats(authorization)


@app.post("/api/agent/entities/search")
async def post_entity_search(
    body: EntitySearchBody,
    authorization: str | None = Header(default=None),
):
    """实体术语试检索（设备/变量等）。"""
    from app.api import entities as entities_api

    return await entities_api.entity_search(body, authorization)


@app.get("/api/agent/knowledge/stats")
async def get_knowledge_stats(authorization: str | None = Header(default=None)):
    """文档知识库统计（Qdrant platform_knowledge）。"""
    from app.api import knowledge as knowledge_api

    return await knowledge_api.knowledge_stats(authorization)


@app.get("/api/agent/knowledge/points")
async def get_knowledge_points(
    limit: int = 20,
    source_contains: str | None = None,
    authorization: str | None = Header(default=None),
):
    """分页浏览知识片段（非语义）。"""
    from app.api import knowledge as knowledge_api

    return await knowledge_api.knowledge_list(
        limit=limit,
        source_contains=source_contains,
        authorization=authorization,
    )


@app.get("/api/agent/knowledge/documents")
async def get_knowledge_documents(
    page: int = 1,
    page_size: int = 20,
    source_contains: str | None = None,
    authorization: str | None = Header(default=None),
):
    """按 source 聚合的文档列表（页码分页）。"""
    from app.api import knowledge as knowledge_api

    return await knowledge_api.knowledge_documents(
        page=page,
        page_size=page_size,
        source_contains=source_contains,
        authorization=authorization,
    )


@app.post("/api/agent/knowledge/search")
async def post_knowledge_search(
    body: KnowledgeSearchBody,
    authorization: str | None = Header(default=None),
):
    """语义试检索。"""
    from app.api import knowledge as knowledge_api

    return await knowledge_api.knowledge_search(body, authorization)


@app.post("/api/agent/knowledge/ingest")
async def post_knowledge_ingest(
    file: Annotated[UploadFile, File()],
    authorization: str | None = Header(default=None),
):
    """上传文件入库（同名自动替换）。"""
    from app.api import knowledge as knowledge_api

    return await knowledge_api.knowledge_ingest(file, authorization)


@app.post("/api/agent/knowledge/replace")
async def post_knowledge_replace(
    file: Annotated[UploadFile, File()],
    source: Annotated[str, Form()],
    authorization: str | None = Header(default=None),
):
    """按已有 source 上传更新（保留 source 键）。"""
    from app.api import knowledge as knowledge_api

    return await knowledge_api.knowledge_replace(file, source=source, authorization=authorization)


@app.post("/api/agent/knowledge/export")
async def post_knowledge_export(
    body: KnowledgeExportBody,
    authorization: str | None = Header(default=None),
):
    """导出文档正文供本地下载（优先磁盘，否则拼接片段）。"""
    from app.api import knowledge as knowledge_api

    return await knowledge_api.knowledge_export(body, authorization)


@app.delete("/api/agent/knowledge/by-source")
async def delete_knowledge_by_source(
    body: KnowledgeDeleteBody,
    authorization: str | None = Header(default=None),
):
    """按 payload.source 精确删除（不提供 drop collection）。"""
    from app.api import knowledge as knowledge_api

    return await knowledge_api.knowledge_delete(body, authorization)


@app.get("/api/agent/voiceprints")
async def get_voiceprints():
    """声纹库列表。"""
    from app.api import voiceprints as voiceprints_api

    return await voiceprints_api.list_voiceprints()


@app.get("/api/agent/voiceprints/config")
async def get_voiceprint_config():
    """声纹门禁配置（桌面与 Agent 共用 VOICEPRINT_ENABLED）。"""
    from app.api import voiceprints as voiceprints_api

    return await voiceprints_api.voiceprint_config()


@app.post("/api/agent/voiceprints")
async def post_voiceprint(body: VoiceprintCreateBody):
    """新建声纹用户。"""
    from app.api.voiceprints import create_voiceprint

    return await create_voiceprint(body)


@app.patch("/api/agent/voiceprints/{profile_id}")
async def patch_voiceprint(profile_id: str, body: VoiceprintUpdateBody):
    """更新声纹用户名称/备注。"""
    from app.api.voiceprints import update_voiceprint

    return await update_voiceprint(profile_id, body)


@app.delete("/api/agent/voiceprints/{profile_id}")
async def remove_voiceprint(profile_id: str):
    """删除声纹用户。"""
    from app.api import voiceprints as voiceprints_api

    return await voiceprints_api.delete_voiceprint(profile_id)


@app.post("/api/agent/voiceprints/{profile_id}/enroll")
async def post_voiceprint_enroll(
    profile_id: str,
    file: Annotated[UploadFile, File()],
    sample_rate: Annotated[int | None, Form()] = 16000,
    device_hint: Annotated[str | None, Form()] = "",
    env_hint: Annotated[str | None, Form()] = "",
):
    """为指定用户录入一段声纹样本（PCM16/WAV；需累计至最少段数才 enrolled）。"""
    from app.api import voiceprints as voiceprints_api

    return await voiceprints_api.enroll_voiceprint(
        profile_id,
        file,
        sample_rate,
        device_hint,
        env_hint,
    )


@app.get("/api/agent/voiceprints/{profile_id}/samples")
async def get_voiceprint_samples(profile_id: str):
    """列出用户已录入样本元数据。"""
    from app.api import voiceprints as voiceprints_api

    return await voiceprints_api.list_samples(profile_id)


@app.delete("/api/agent/voiceprints/{profile_id}/samples/{sample_id}")
async def remove_voiceprint_sample(profile_id: str, sample_id: str):
    """删除单段声纹模板。"""
    from app.api import voiceprints as voiceprints_api

    return await voiceprints_api.delete_sample(profile_id, sample_id)


@app.post("/api/agent/voiceprints/verify")
async def post_voiceprint_verify(
    profile_id: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    sample_rate: Annotated[int | None, Form()] = 16000,
    scene: Annotated[str | None, Form()] = "assistant_gate",
):
    """1:1 核验当前说话人是否匹配所选声纹用户。"""
    from app.api import voiceprints as voiceprints_api

    return await voiceprints_api.verify_voiceprint(profile_id, file, sample_rate, scene)


@app.post("/api/agent/voiceprints/identify")
async def post_voiceprint_identify(
    file: Annotated[UploadFile, File()],
    sample_rate: Annotated[int | None, Form()] = 16000,
    scene: Annotated[str | None, Form()] = "identify_open",
    top_k: Annotated[int | None, Form()] = None,
):
    """1:N 识别说话人（库内 Top-K）。"""
    from app.api import voiceprints as voiceprints_api

    return await voiceprints_api.identify_voiceprint(file, sample_rate, scene, top_k)


@app.post("/api/agent/chat")
async def post_chat(request: Request, body: chat.ChatRequest):
    """
    主对话接口：SSE 流式返回 Agent 回复。

    Request：原始 HTTP 请求（可读 header、client）
    body：Pydantic 模型，FastAPI 自动从 JSON body 解析
    """
    return await chat.chat_sse(request, body)


@app.post("/api/agent/resume")
async def post_resume(request: Request, body: resume.ResumeRequest):
    """HITL 中断后用户提交表单，恢复 Agent 执行。"""
    return await resume.resume_sse(request, body)


@app.post("/api/agent/transcribe")
async def post_transcribe(
    file: Annotated[UploadFile, File()],
    model_id: Annotated[str | None, Form()] = None,
):
    """
    语音转写：multipart 上传音频文件。

    Annotated[UploadFile, File()]：告诉 FastAPI 从表单文件字段读取
    Form()：可选的 model_id 表单字段
    """
    return await transcribe.transcribe_audio(file, model_id)


@app.post("/api/agent/transcribe/stream/start")
async def post_transcribe_stream_start(
    model_id: Annotated[str | None, Form()] = None,
):
    """流式转写：创建并行分片会话。"""
    return await transcribe.stream_start(model_id)


@app.post("/api/agent/transcribe/stream/chunk")
async def post_transcribe_stream_chunk(
    file: Annotated[UploadFile, File()],
    session_id: Annotated[str, Form()],
    seq: Annotated[int, Form()],
    model_id: Annotated[str | None, Form()] = None,
):
    """流式转写：提交分片（并行 ASR+纠错，立即返回）。"""
    return await transcribe.stream_chunk(file, session_id, seq, model_id)


@app.post("/api/agent/transcribe/stream/finish")
async def post_transcribe_stream_finish(
    session_id: Annotated[str, Form()],
):
    """流式转写：收敛并行结果并返回最终文本。"""
    return await transcribe.stream_finish(session_id)


@app.websocket("/api/agent/transcribe/realtime")
async def ws_transcribe_realtime(websocket: WebSocket):
    """Realtime ASR：词级 partial + stop 后多级纠错。"""
    from app.services.voice.realtime_bridge import handle_realtime_transcribe

    await handle_realtime_transcribe(websocket)


# Agent MCP Gateway：REST + Streamable HTTP /mcp
from app.mcp.gateway import mount_agent_mcp_gateway  # noqa: E402

mount_agent_mcp_gateway(app)
app.mount("/mcp", _gateway_http_app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.port, reload=True)
