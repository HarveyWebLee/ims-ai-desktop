"""
BPMN 级流程编排 REST API 模块

文件职责
--------
与前端 `BpmnFlowgram` 画布对接，提供「Plan 步骤 ↔ 画布 JSON」互转、
画布结构校验，以及按 thread_id 读写 BPMN 编排快照（草稿 / 批准后落库）。

白话概念
--------
Plan 是 Agent 拆好的「步骤清单」；BPMN 画布是值班员可拖拽编辑的流程图。
本模块负责两边格式互转，并把用户改过的草稿挂到当前对话线程上，
下次打开同一会话还能看到。

在 Agent 流程中的位置
--------------------
  plan_confirm / 编排 UI
    → 前端 BpmnFlowgram
    → 本模块 convert / validate / threads/{id}/bpmn
    → session_store 持久化 snapshot（内存或 Postgres）
  用户批准 Plan 后，执行仍走 stream_chat / stream_resume，本模块不直接跑工具。

如何被调用
----------
- 路由注册：`app/main.py`（POST convert、POST validate、GET/PUT threads/{id}/bpmn）
- 读/写快照前：Postgres 模式下经 `can_read_thread` 做会话读权限校验
- 响应：统一 `{ code, data, message }`（`ok` / `fail`）
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.api.response import fail, ok
from app.api.thread_access import can_read_thread
from app.middleware.auth import get_current_user_id
from app.persistence.bootstrap import is_postgres_enabled
from app.services.bpmn_orchestration import (
    build_bpmn_snapshot,
    count_active_plan_steps,
    flow_document_to_plan_steps,
    merge_bpmn_steps_with_previous,
    plan_steps_to_flow_document,
    validate_flow_document,
)
from app.services.session_store import session_store


class BpmnConvertRequest(BaseModel):
    """
    画布与 Plan 互转请求体。

    字段
    ----
    direction : Literal
        ``steps_to_document``：Plan 步骤列表 → Flowgram 画布 JSON；
        ``document_to_steps``：画布 JSON → Plan 步骤列表。
    steps : list | None
        ``steps_to_document`` 时必填；每项为 Plan 步骤 dict。
    flow_document : dict | None
        ``document_to_steps`` 时必填；前端画布文档。
    previous_steps : list | None
        仅 ``document_to_steps``：与既有 Plan 合并状态（保留完成/失败等），
        避免画布回写把执行进度抹掉。
    """

    direction: Literal["steps_to_document", "document_to_steps"]
    steps: list[dict[str, Any]] | None = None
    flow_document: dict[str, Any] | None = None
    previous_steps: list[dict[str, Any]] | None = Field(
        default=None,
        description="document_to_steps 时与既有 Plan 合并状态",
    )


class BpmnValidateRequest(BaseModel):
    """画布校验请求：只需提交前端当前的 flow_document。"""

    flow_document: dict[str, Any]


class BpmnSnapshotSaveRequest(BaseModel):
    """
    保存线程 BPMN 快照的请求体。

    flow_document 与 steps 至少提供一个；graph 为可选拓扑摘要。
    """

    flow_document: dict[str, Any] | None = None
    steps: list[dict[str, Any]] | None = None
    graph: dict[str, Any] | None = None


async def convert_bpmn(body: BpmnConvertRequest, authorization: str | None = None):
    """
    POST /api/agent/bpmn/convert — 步骤与画布 JSON 互转。

    参数
    ----
    body : BpmnConvertRequest
        互转方向与对应载荷。
    authorization : str | None
        预留 Authorization（本接口当前不强制鉴权）。

    返回
    ----
    成功时 data 含 flow_document / steps（及 document_to_steps 时的 active_step_count）；
    参数缺失时 fail(40001)。
    """
    if body.direction == "steps_to_document":
        if not body.steps:
            return fail(40001, "参数错误", "steps 不能为空")
        doc = plan_steps_to_flow_document(body.steps)
        return ok(
            {
                "flow_document": doc,
                "steps": body.steps,
            }
        )

    if not body.flow_document:
        return fail(40001, "参数错误", "flow_document 不能为空")

    # convert 与 validate 对齐：多分支条件不可静默丢支
    validation = validate_flow_document(body.flow_document)
    if not validation.get("valid"):
        errs = validation.get("errors") or ["画布校验失败"]
        return fail(40002, "画布校验失败", "; ".join(str(e) for e in errs))

    try:
        extracted = flow_document_to_plan_steps(body.flow_document)
    except ValueError as exc:
        return fail(40002, "画布转换失败", str(exc))

    # 有上一轮 Plan 时合并状态，保留已完成步骤等
    if body.previous_steps:
        steps = merge_bpmn_steps_with_previous(extracted, body.previous_steps)
    else:
        steps = extracted

    return ok(
        {
            "steps": steps,
            "flow_document": body.flow_document,
            "active_step_count": count_active_plan_steps(steps),
        }
    )


async def validate_bpmn(body: BpmnValidateRequest, authorization: str | None = None):
    """
    POST /api/agent/bpmn/validate — 校验画布结构是否可转为可执行 Plan。

    返回 data 为 validate_flow_document 的结果（含 valid、errors 等字段）。
    """
    if not body.flow_document:
        return fail(40001, "参数错误", "flow_document 不能为空")
    result = validate_flow_document(body.flow_document)
    return ok(result)


async def get_thread_bpmn(thread_id: str, authorization: str | None = None):
    """
    GET /api/agent/threads/{thread_id}/bpmn — 读取线程 BPMN 快照。

    参数
    ----
    thread_id : str
        对话线程 ID。
    authorization : str | None
        Bearer JWT；用于解析 user_id 并做读权限校验。

    返回
    ----
    data = { thread_id, snapshot }；无快照时 snapshot 为 None。
    Postgres 下无权访问则 fail(40404)。
    """
    if not thread_id:
        return fail(40001, "参数错误", "thread_id 不能为空")

    user_id = await get_current_user_id(authorization)
    if is_postgres_enabled() and not can_read_thread(user_id, thread_id):
        return fail(40404, "会话不存在", "无权访问该会话")

    snapshot = session_store.get_thread_bpmn_snapshot(thread_id)
    if not snapshot:
        return ok({"thread_id": thread_id, "snapshot": None})

    return ok({"thread_id": thread_id, "snapshot": snapshot})


async def save_thread_bpmn(
    thread_id: str,
    body: BpmnSnapshotSaveRequest,
    authorization: str | None = None,
):
    """
    PUT /api/agent/threads/{thread_id}/bpmn — 保存线程 BPMN 快照。

    若带 flow_document，先做结构校验，不合法则 fail(40002) 并附校验详情。
    成功后写入 session_store，返回完整 snapshot。
    """
    if not thread_id:
        return fail(40001, "参数错误", "thread_id 不能为空")
    if not body.flow_document and not body.steps:
        return fail(40001, "参数错误", "flow_document 与 steps 至少提供一个")

    user_id = await get_current_user_id(authorization)
    if is_postgres_enabled() and not can_read_thread(user_id, thread_id):
        return fail(40404, "会话不存在", "无权访问该会话")

    if body.flow_document:
        validation = validate_flow_document(body.flow_document)
        if not validation.get("valid"):
            return fail(
                40002,
                "BPMN 画布校验失败",
                validation,
            )

    snapshot = build_bpmn_snapshot(
        steps=body.steps,
        flow_document=body.flow_document,
        graph=body.graph,
    )
    session_store.set_thread_bpmn_snapshot(thread_id, snapshot)
    return ok({"thread_id": thread_id, "snapshot": snapshot})
