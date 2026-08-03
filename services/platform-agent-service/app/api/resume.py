"""
HITL 恢复（Resume）SSE API 模块

文件职责
--------
提供 `POST /api/agent/resume` 的处理逻辑：
当 LangGraph 在 Human-in-the-Loop（HITL）节点 interrupt 暂停后，
前端提交用户决策（批准 / 拒绝 / 补参 respond），本接口恢复图执行并继续 SSE 推送。

在 Agent 流程中的位置
--------------------
  chat_sse → stream_chat → 图在 confirm 或 collect_params 处 interrupt
    → 前端收到 interrupt SSE，展示确认框或表单
    → 用户操作 → resume_sse → stream_resume → 图从 checkpoint 继续
  与 chat 共用 `_sse_from_stream` 做 SSE 格式化。

如何被调用
----------
- 路由：`app/main.py` 中 `@app.post("/api/agent/resume")`
- 请求体：`ResumeRequest`（thread_id、decisions 数组、可选 model_id）
- 响应：与 chat 相同的 text/event-stream
"""

# ---------------------------------------------------------------------------
# 标准库
# ---------------------------------------------------------------------------
from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# 第三方
# ---------------------------------------------------------------------------
from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# 本项目：复用 chat 模块的 SSE 包装器，避免重复实现
# ---------------------------------------------------------------------------
from app.api.chat import _sse_from_stream

# ---------------------------------------------------------------------------
# 本项目
# ---------------------------------------------------------------------------
from app.api.response import fail
from app.application.conversation.resume import stream_resume
from app.middleware.auth import get_current_user_id
from app.models.catalog import get_catalog_item, get_default_model_id
from app.services.audit_store import audit_store, mask_payload_summary
from contracts.context import normalize_run_mode


class ResumeDecision(BaseModel):
    """
    单条 HITL 决策。

    字段
    ----
    type : str
        决策类型，常见值：
        - "approve"：用户确认执行（如批量确认告警）
        - "reject"：用户拒绝
        - "respond"：用户填写缺失参数或自定义回复
        其他 type 会原样 model_dump 传给 LangGraph。
    args : dict | None
        type 为 respond 时的表单字段；approve/reject 通常为空。
    """

    type: str
    args: dict[str, Any] | None = None


class ResumeRequest(BaseModel):
    """
    POST /api/agent/resume 请求体。

    字段
    ----
    thread_id : str
        须与 interrupt 时 chat 使用的 thread_id 一致。
    mid : str | None
        用户本轮需求 ID；须与产生 interrupt 的 chat mid 一致。省略时从 checkpoint HumanMessage 回退。
    model_id : str | None
        恢复执行时使用的模型，默认 catalog 默认项。
    decisions : list[ResumeDecision]
        LangGraph HITL API 支持多条 decision；当前实现取 decisions[0] 为主决策。
    run_mode : str | None
        会话运行模式；须与产生 interrupt 的 chat 一致；缺省 confirm。
    plan_first : bool
        与 chat 对称透传（续跑不再 classify，主要用于审计/一致性）。
    """

    thread_id: str = Field(..., min_length=1)
    mid: str | None = None
    model_id: str | None = None
    decisions: list[ResumeDecision] = Field(..., min_length=1)
    run_mode: str | None = None
    plan_first: bool = False

    @field_validator("run_mode", mode="before")
    @classmethod
    def _normalize_run_mode(cls, value: Any) -> str:
        return normalize_run_mode(str(value) if value is not None else None)


async def resume_sse(request: Request, body: ResumeRequest):
    """
    接收 HITL 决策并恢复 Agent 图执行，返回 SSE 流。

    参数
    ----
    request : Request
        用于读取 Authorization。
    body : ResumeRequest
        已校验的请求体。

    返回
    ----
    JSONResponse | StreamingResponse
        decisions 无效或 model_id 非法 → HTTP 400 JSON
        成功 → SSE 流（与 chat 相同事件类型）

    业务说明
    --------
    - 将前端 decision 映射为 LangGraph resume_value 结构
    - approve/reject/respond 写入 audit_store 供合规追溯
    - 审计写入失败被静默忽略（pass），不影响主流程
    """
    if not body.decisions:
        return JSONResponse(fail(40003, "resume 失败", "decisions 格式无效"), status_code=400)

    model_id = body.model_id or get_default_model_id()
    if not get_catalog_item(model_id):
        return JSONResponse(
            fail(40001, "参数错误", "model_id 不在模型目录中或已禁用"),
            status_code=400,
        )

    # 当前仅处理第一条 decision（与前端单步 HITL UI 对齐）
    decision = body.decisions[0]
    if decision.type == "approve":
        resume_value: dict[str, Any] = {"type": "approve", "approved": True}
        # Phase D4 / BPMN：plan_confirm 编排后携带 steps / graph / flow_document
        if decision.args:
            flow_doc = decision.args.get("flow_document")
            if isinstance(flow_doc, dict):
                from app.services.bpmn_orchestration import validate_flow_document

                validation = validate_flow_document(flow_doc)
                if not validation.get("valid"):
                    return JSONResponse(
                        fail(40002, "BPMN 画布校验失败", validation),
                        status_code=400,
                    )
            if isinstance(decision.args.get("steps"), list):
                resume_value["steps"] = decision.args["steps"]
            if isinstance(decision.args.get("graph"), dict):
                resume_value["graph"] = decision.args["graph"]
            if isinstance(decision.args.get("flow_document"), dict):
                resume_value["flow_document"] = decision.args["flow_document"]
            if isinstance(decision.args.get("params_by_tool"), dict):
                resume_value["params_by_tool"] = decision.args["params_by_tool"]
    elif decision.type == "reject":
        resume_value = {"type": "reject", "approved": False}
    elif decision.type == "respond":
        # respond：resume_value 即为用户提交的参数字典
        resume_value = decision.args or {}
    else:
        # 未知 type：整模型转 dict 传给 graph，便于扩展新 HITL 类型
        resume_value = decision.model_dump()

    from contracts.agent_debug import agent_debug

    agent_debug(
        "flow.api.resume",
        thread_id=body.thread_id,
        mid=(body.mid or "").strip() or None,
        decision_type=decision.type,
        hitl_tool=((decision.args or {}).get("_hitl_tool") if decision.type == "respond" else None),
        arg_keys=list((decision.args or {}).keys()) if decision.args else [],
    )

    authorization = request.headers.get("authorization")
    user_id = await get_current_user_id(authorization)

    # HITL 确认/拒绝：写入审计（与 Trace 分离，避免重复）
    if decision.type == "approve":
        audit_event = "confirm_approve"
        hitl_action = "approve"
    elif decision.type == "reject":
        audit_event = "confirm_reject"
        hitl_action = "reject"
    elif decision.type == "respond":
        audit_event = "confirm_respond"
        hitl_action = "approve"
    else:
        audit_event = f"confirm_{decision.type}"
        hitl_action = None
    try:
        audit_store.append(
            thread_id=body.thread_id,
            user_id=user_id,
            event_type=audit_event,
            # mask_payload_summary：脱敏后仅存摘要，避免敏感参数落库
            payload_summary=mask_payload_summary(
                {"decision_type": decision.type, "args": decision.args}
            ),
        )
    except Exception:
        # 审计非关键路径，失败不阻断 resume
        pass

    if hitl_action is not None:
        try:
            from app.services.bpmn_observability import record_hitl_lifecycle

            interrupt_type = None
            tool_name = None
            if isinstance(decision.args, dict):
                tool_name = decision.args.get("_hitl_tool") or decision.args.get("tool")
            record_hitl_lifecycle(
                action=hitl_action,  # type: ignore[arg-type]
                interrupt_type=str(interrupt_type or decision.type),
                tool=str(tool_name) if tool_name else None,
                thread_id=body.thread_id,
                user_id=user_id,
            )
        except Exception:
            pass

    return await _sse_from_stream(
        stream_resume(
            thread_id=body.thread_id,
            model_id=model_id,
            resume_value=resume_value,
            auth_token=authorization,
            user_id=user_id,
            mid=body.mid,
            run_mode=body.run_mode,
            plan_first=body.plan_first,
        ),
        thread_id=body.thread_id,
    )
