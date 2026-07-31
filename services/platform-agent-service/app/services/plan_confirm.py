"""
Phase C2：多步 Plan 执行前确认（plan_confirm HITL）。

文件职责
--------
在真正执行多步工具之前，组装「请用户确认是否按此计划执行」的门控：
步骤条、预填参数、graph / BPMN 画布、以及 resume_hint（调试/测试用元数据）。
同时提供规则参数推断、告警筛选向导出/批量步传播、导航 path 从 label 解析等。

在 Agent 流程中的位置
--------------------
    stream_chat
      → prepare_plan_confirm_gate_async
          → evaluate_plan_route（同步分流）
          → resolve_task_plan + 可选 LLM 参数
          → prepare_plan_confirm_gate → interrupt(type=plan_confirm)
    用户批准
      → resume → Command(resume) → 父图 plan_execute
    用户拒绝 / 新消息
      → Command(resume=reject) 或新 chat 结束 checkpoint interrupt

路由收敛（plan_route.evaluate_plan_route）
----------------------------------------
    ≥2 步且 plan_needs_user_confirm → 显式 Plan + plan_confirm
    其余 → ReAct + PlanTracker 动态对齐

如何被调用
----------
- 主入口：``prepare_plan_confirm_gate_async``（生产 async 路径）
- 同步/测试：``prepare_plan_confirm_gate``（可注入 raw_plan / llm_params）
- 占位工具名：``PLAN_CONFIRM_TOOL = "__plan__"``（非真实工具）
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from platform_mcp.runtime.time_range import extract_alarm_time_range_from_message

from app.config import settings
from app.graph.context import AgentContext
from app.services.task_planner import build_task_plan, extract_alarm_status_from_message

# plan_confirm interrupt 占位 tool 名（非真实工具）
PLAN_CONFIRM_TOOL = "__plan__"

# 只读类工具：多步 Plan 若仅含这些工具且 write_only 开启，可跳过 plan_confirm
READ_ONLY_PLAN_TOOLS = frozenset(
    {
        "query_alarms",
        "get_alarm_detail",
        "navigate_to",
        "open_alarm_detail",
        "query_devices",
        "get_device_detail",
        "query_device_variables",
        "open_device_detail",
    }
)


def _write_plan_tools() -> frozenset[str]:
    """从 catalog risk_level 读取 medium/high 写操作工具（export 后生效）。"""
    from platform_mcp.runtime.tool_catalog_loader import get_tools_by_risk

    names = get_tools_by_risk("medium", "high")
    # catalog 未导出时的兜底，避免 plan_confirm 门控失效
    if not names:
        return frozenset({"download_file", "batch_confirm_alarms", "batch_process_alarms"})
    return names


# query_alarms 与 download_file(alarm_report) 共用的筛选参数字段
_ALARM_QUERY_TO_EXPORT_KEYS = (
    "start_time",
    "end_time",
    "status",
    "alarm_category_id",
    "alarm_rank_id",
    "alarm_level",
)

# 从用户原话抽取相对时间片段（供 query_alarms / download_file 预填 start_time）
# 绝对时间与命名参数见 time_range.extract_alarm_time_range_from_message

# 导航目标片段（「打开设备管理然后…」）
_NAV_TARGET_RE = re.compile(
    r"(?:打开|跳转|导航到?|进入)\s*(.+?)(?:然后|接着|再|之后|并|，|,|$)",
)


@dataclass(frozen=True)
class PlanConfirmGate:
    """
    Plan 执行前确认门控产物。

    - steps：展示用步骤（status 多为 awaiting_confirm）
    - params_by_tool：按工具名预填的参数（父图写入 ParentState 供续跑）
    - interrupt_payload：立刻发给前端的 SSE interrupt 主体
    - resume_hint：与 interrupt/steps 对齐的元数据副本（非 session pending；
      父图续跑读 ParentState / checkpoint，不读本字段）
    """

    steps: list[dict[str, Any]]
    params_by_tool: dict[str, dict[str, Any]]
    interrupt_payload: dict[str, Any]
    resume_hint: dict[str, Any]


def extract_nav_target(message: str) -> str:
    """从用户消息中提取导航目标片段。"""
    m = _NAV_TARGET_RE.search((message or "").strip())
    if m:
        return m.group(1).strip()[:64]
    return ""


def nav_path_from_step_label(label: str) -> str:
    """
    从 Plan 步骤 label（如「跳转到设施页面」）提取 navigate_to 的 path 参数。

    复合 Plan 中连续多步 navigate_to 时，每步 label 由 task_planner 从子句生成，
    应优先用 label 而非整句消息的首个导航目标。
    """
    text = (label or "").strip()
    m = re.match(r"跳转到\s*(.+)", text)
    if not m:
        return ""
    target = m.group(1).strip().rstrip("，,。.")
    if target.startswith("到"):
        target = target[1:].strip()
    # 停留时长写在同一步 label 时，path 只保留页面名称
    target = re.sub(r"[，,]?\s*停留\s*\d+\s*s", "", target, flags=re.I).strip()
    return target[:64]


def resolve_step_tool_params(
    step: dict[str, Any],
    params_by_tool: dict[str, dict[str, Any]],
    user_message: str = "",
) -> dict[str, Any]:
    """
    解析单步 Plan 的工具参数。

    同一工具出现多次（如连续 navigate_to）时，优先从步骤 label 推导路径，
    避免 params_by_tool 以工具名为键导致后续步骤复用首步参数。
    """
    tool_name = str(step.get("tool") or "")
    if not tool_name:
        return {}

    if tool_name == "navigate_to":
        path = nav_path_from_step_label(str(step.get("label") or ""))
        if path:
            return {"path": path}
        fallback = extract_nav_target(user_message) or (user_message or "")[:64]
        if fallback:
            return {"path": fallback}

    if tool_name == "pause":
        step_params = step.get("params")
        if isinstance(step_params, dict) and step_params.get("seconds") is not None:
            return {"seconds": int(step_params["seconds"])}
        pause_m = re.search(r"停留\s*(\d+)\s*秒", str(step.get("label") or ""))
        if pause_m:
            return {"seconds": int(pause_m.group(1))}
        return {"seconds": 1}

    return dict(params_by_tool.get(tool_name) or {})


def _alarm_param_has_value(value: Any) -> bool:
    """判断告警筛选参数是否非空。"""
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    if isinstance(value, (list, dict)) and not value:
        return False
    return True


def propagate_query_alarm_params_to_export(
    params_by_tool: dict[str, dict[str, Any]],
    steps: list[dict[str, Any]] | None = None,
) -> None:
    """
    将 query_alarms 已确认的筛选条件复用到同计划内的 download_file。

    典型场景：「查告警并导出」Plan 中，查询步经 HITL 补选时间后，
    导出步应沿用相同时间/筛选，避免使用者重复填写。
    就地修改 params_by_tool。
    """
    from platform_mcp.runtime.tools.alarm import _resolve_or_prepare_alarm_times

    query_params = params_by_tool.get("query_alarms")
    if not query_params:
        return

    if steps is not None:
        has_pending_export = any(
            str(step.get("tool")) == "download_file"
            and str(step.get("status")) in ("pending", "running")
            for step in steps
        )
        if not has_pending_export:
            return

    export_params = dict(params_by_tool.get("download_file") or {})
    resource = str(export_params.get("resource") or "alarm_report").strip()
    # 非告警导出走独立参数，不复用 query_alarms 的 status/device 等
    if resource != "alarm_report":
        return

    if not export_params.get("resource"):
        export_params["resource"] = "alarm_report"

    export_start = str(export_params.get("start_time") or "")
    export_end = str(export_params.get("end_time") or "")
    _, _, export_needs_time = _resolve_or_prepare_alarm_times(export_start, export_end)

    for key in _ALARM_QUERY_TO_EXPORT_KEYS:
        value = query_params.get(key)
        if not _alarm_param_has_value(value):
            continue
        if key in ("start_time", "end_time"):
            if not export_needs_time:
                continue
        elif _alarm_param_has_value(export_params.get(key)):
            continue
        export_params[key] = value

    params_by_tool["download_file"] = export_params


def propagate_query_alarm_params_to_batch(
    params_by_tool: dict[str, dict[str, Any]],
    steps: list[dict[str, Any]] | None = None,
) -> None:
    """
    将 query_alarms 已确认的筛选条件复用到同计划内的 batch_* 步骤。

    典型场景：「查告警并导出然后批量处理」中，查询步补选时间后，
    批量处理步应沿用相同时间/状态筛选。
    """
    from platform_mcp.runtime.tools.alarm import _resolve_or_prepare_alarm_times

    query_params = params_by_tool.get("query_alarms")
    if not query_params:
        return

    batch_tools = ("batch_process_alarms", "batch_confirm_alarms")
    if steps is not None:
        planned = {str(s.get("tool") or "") for s in steps}
        batch_tools = tuple(t for t in batch_tools if t in planned)
        if not batch_tools:
            return

    for tool_name in batch_tools:
        batch_params = dict(params_by_tool.get(tool_name) or {})
        batch_start = str(batch_params.get("start_time") or "")
        batch_end = str(batch_params.get("end_time") or "")
        _, _, batch_needs_time = _resolve_or_prepare_alarm_times(batch_start, batch_end)

        for key in _ALARM_QUERY_TO_EXPORT_KEYS:
            value = query_params.get(key)
            if not _alarm_param_has_value(value):
                continue
            if key in ("start_time", "end_time"):
                if not batch_needs_time:
                    continue
            elif _alarm_param_has_value(batch_params.get(key)):
                continue
            batch_params[key] = value

        params_by_tool[tool_name] = batch_params


def propagate_query_alarm_filter_params(
    params_by_tool: dict[str, dict[str, Any]],
    steps: list[dict[str, Any]] | None = None,
) -> None:
    """将 query_alarms 筛选条件复用到同计划内的导出与批量写操作步骤。"""
    propagate_query_alarm_params_to_export(params_by_tool, steps)
    propagate_query_alarm_params_to_batch(params_by_tool, steps)


def infer_plan_params(
    message: str,
    steps: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """
    为规则 Plan 各步骤推断初始工具参数（最小可用）。

    设备类槽位不在此用正则猜测；条件图路径由 Flow IR.args 提供。
    缺参时工具内仍会触发 ask_params HITL。
    """
    msg = (message or "").strip()
    start_time, end_time = extract_alarm_time_range_from_message(msg)
    alarm_status = extract_alarm_status_from_message(msg)
    nav_target = extract_nav_target(msg)
    params_by_tool: dict[str, dict[str, Any]] = {}

    for step in steps:
        tool = str(step.get("tool") or "")
        if not tool or tool in params_by_tool:
            continue
        if tool == "query_alarms":
            query_params: dict[str, Any] = {
                "start_time": start_time,
                "end_time": end_time,
            }
            if alarm_status:
                query_params["status"] = alarm_status
            params_by_tool[tool] = query_params
        elif tool == "download_file":
            from platform_mcp.runtime.tools.export import infer_download_resource

            resource = infer_download_resource(msg)
            export_params: dict[str, Any] = {
                "resource": resource,
                "start_time": start_time,
                "end_time": end_time,
            }
            if resource == "alarm_report" and alarm_status:
                export_params["status"] = alarm_status
            params_by_tool[tool] = export_params
        elif tool == "navigate_to":
            params_by_tool[tool] = {"path": nav_target or msg[:64]}
        elif tool == "get_alarm_detail":
            params_by_tool[tool] = {}
        elif tool in ("batch_process_alarms", "batch_confirm_alarms"):
            batch_params: dict[str, Any] = {
                "start_time": start_time,
                "end_time": end_time,
            }
            if alarm_status:
                batch_params["status"] = alarm_status
            params_by_tool[tool] = batch_params

    return params_by_tool


def merge_plan_params(
    message: str,
    steps: list[dict[str, Any]],
    *,
    llm_params: dict[str, dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    """
    规则 infer + LLM 抽取合并：LLM 合法值覆盖规则层，规则层仍作兜底。
    """
    from app.services.llm_plan_params import merge_tool_params, sanitize_llm_tool_params

    merged = infer_plan_params(message, steps)
    if not llm_params:
        return merged

    step_tools = {str(s.get("tool") or "") for s in steps if s.get("tool")}
    for tool, raw in llm_params.items():
        if tool not in step_tools:
            continue
        sanitized = sanitize_llm_tool_params(tool, raw)
        if not sanitized:
            continue
        base = dict(merged.get(tool) or {})
        merged[tool] = merge_tool_params(base, sanitized)
    return merged


def plan_needs_user_confirm(steps: list[dict[str, Any]]) -> bool:
    """
    判断多步 Plan 是否需要 plan_confirm 门控。

    write_only=True 时：纯只读多步（如 导航+查询）跳过；含导出/批量确认等则必须确认。
    write_only=False 时：凡 ≥2 步规则 Plan 均需确认。
    """
    # 总开关「凡多步都确认」：不区分读写
    if not settings.agent_plan_confirm_write_only:
        return True

    tools = {str(step.get("tool") or "") for step in steps if step.get("tool")}
    if not tools:
        return False
    # 命中 catalog medium/high（写操作）→ 必须门控
    if tools & _write_plan_tools():
        return True
    # 含未列入只读清单的工具（未来扩展）时保守要求确认
    if not tools.issubset(READ_ONLY_PLAN_TOOLS):
        return True
    # 纯 READ_ONLY_PLAN_TOOLS → 跳过 plan_confirm，走 ReAct
    return False


def _normalize_steps(
    steps: list[dict[str, Any]],
    *,
    initial_status: str = "pending",
) -> list[dict[str, Any]]:
    """确保每步含 id/label/status，过滤无 tool 的步骤。"""
    normalized: list[dict[str, Any]] = []
    for i, step in enumerate(steps, 1):
        tool = step.get("tool")
        if not tool:
            continue
        normalized.append(
            {
                "id": str(step.get("id") or i),
                "label": str(step.get("label") or tool),
                "tool": str(tool),
                # plan_confirm 等场景用 initial_status 覆盖规则 Plan 自带的 pending
                "status": (
                    initial_status
                    if initial_status != "pending"
                    else str(step.get("status") or initial_status)
                ),
            }
        )
    return normalized


def prepare_plan_confirm_gate(
    ctx: AgentContext,
    *,
    model_id: str | None = None,
    raw_plan: list[dict[str, Any]] | None = None,
    llm_params: dict[str, dict[str, Any]] | None = None,
    flow_document: dict[str, Any] | None = None,
    ir_params_by_tool: dict[str, dict[str, Any]] | None = None,
) -> PlanConfirmGate | None:
    """
    若当前消息命中多步 Plan 且开关开启，返回 plan_confirm 门控。

    参数:
        ctx: 已组装的 Agent 上下文
        model_id: 可选；async 路径已解析 Plan 时可省略
        raw_plan: 可选；由 resolve_task_plan 预解析的多步计划
        flow_document: 可选；P2 编译后的条件画布（覆盖线性 plan_steps_to_flow_document）
        ir_params_by_tool: 可选；Flow IR 节点 args 汇总，优先于规则 infer

    返回:
        PlanConfirmGate 或 None（单步 / 非复合 / 开关关闭）
    """
    if not settings.agent_plan_confirm_enabled:
        return None

    # 优先用上游已解析 Plan（async 路径）；否则现场跑规则 planner
    plan_source = raw_plan
    if plan_source is None:
        plan_source = build_task_plan(ctx.message, metadata=ctx.metadata)

    if not plan_source or len(plan_source) < 2:
        return None

    steps = _normalize_steps(plan_source)
    if len(steps) < 2:
        return None

    # 条件图画布强制走确认；线性只读多步仍可按 write_only 跳过
    has_conditional_doc = False
    if isinstance(flow_document, dict):
        from app.application.execution.bpmn_graph import (
            flow_document_has_executable_conditions,
        )

        has_conditional_doc = flow_document_has_executable_conditions(flow_document)

    if not has_conditional_doc and not plan_needs_user_confirm(steps):
        return None

    # 暂停期间：TaskProgress 展示「待确认」而非「待执行」
    steps = _normalize_steps(plan_source, initial_status="awaiting_confirm")

    # 规则参数 + 可选 LLM 抽取；IR.args 覆盖同名键（设备槽位来源）
    params_by_tool = merge_plan_params(ctx.message, steps, llm_params=llm_params)
    if ir_params_by_tool:
        from app.services.llm_plan_params import merge_tool_params

        for tool, raw in ir_params_by_tool.items():
            if not isinstance(raw, dict) or not raw:
                continue
            base = dict(params_by_tool.get(tool) or {})
            params_by_tool[tool] = merge_tool_params(base, raw)

    step_summary = " → ".join(s["label"] for s in steps)

    interrupt_payload: dict[str, Any] = {
        "type": "plan_confirm",
        "tool": PLAN_CONFIRM_TOOL,
        "message": f"将按以下 {len(steps)} 步执行：{step_summary}。请确认是否开始。",
        "steps": steps,
    }
    from app.services.plan_graph import build_plan_graph

    # 轻量流程图 + BPMN 画布一并塞给前端，便于编排/只读预览
    interrupt_payload["graph"] = build_plan_graph(steps)
    from app.services.bpmn_orchestration import plan_steps_to_flow_document

    interrupt_payload["flow_document"] = (
        flow_document if isinstance(flow_document, dict) else plan_steps_to_flow_document(steps)
    )

    # 与 interrupt 内 steps/graph 对齐的提示副本（测试断言 compile_source 等）
    resume_hint: dict[str, Any] = {
        "steps": steps,
        "params_by_tool": params_by_tool,
        "user_message": ctx.message,
        "graph": interrupt_payload["graph"],
        "flow_document": interrupt_payload["flow_document"],
    }
    if has_conditional_doc:
        resume_hint["compile_source"] = "llm_ir"

    return PlanConfirmGate(
        steps=steps,
        params_by_tool=params_by_tool,
        interrupt_payload=interrupt_payload,
        resume_hint=resume_hint,
    )


async def prepare_plan_confirm_gate_async(
    ctx: AgentContext,
    *,
    model_id: str,
) -> PlanConfirmGate | None:
    """
    Phase D1 / P2：async 门控 — 双灰度下先 LLM IR；否则 resolve_task_plan → plan_confirm。

    P2：由模型判断是否条件任务（空 conditions 即回退），不再用正则猜意图。
    """
    from app.services.llm_flow_compiler import (
        is_llm_flow_compile_enabled,
        try_compile_conditional_plan,
    )
    from app.services.llm_plan_params import generate_llm_plan_params
    from app.services.llm_task_planner import resolve_task_plan
    from app.services.plan_route import PlanExecutionMode, evaluate_plan_route

    # P2：双灰度开启时优先尝试 IR（模型自行判定是否条件图）
    if is_llm_flow_compile_enabled():
        compiled = await try_compile_conditional_plan(
            ctx.message,
            model_id=model_id,
            metadata=ctx.metadata,
        )
        if compiled is not None:
            llm_params = None
            if settings.agent_llm_plan_params_enabled and len(compiled.steps) >= 2:
                plan_steps = _normalize_steps(compiled.steps)
                llm_params = await generate_llm_plan_params(
                    ctx.message,
                    plan_steps,
                    model_id=model_id,
                )
            return prepare_plan_confirm_gate(
                ctx,
                model_id=model_id,
                raw_plan=compiled.steps,
                llm_params=llm_params,
                flow_document=compiled.flow_document,
                ir_params_by_tool=compiled.params_by_tool,
            )

    # 先同步分流：非显式 Plan 立刻返回，避免无谓 LLM Plan 调用
    if evaluate_plan_route(ctx.message, metadata=ctx.metadata) != PlanExecutionMode.EXPLICIT_PLAN:
        return None

    raw_plan = await resolve_task_plan(
        ctx.message,
        metadata=ctx.metadata,
        model_id=model_id,
    )
    llm_params = None
    # 第二轮 LLM：在已有 steps 上抽参数（可单独关）
    if settings.agent_llm_plan_params_enabled and raw_plan and len(raw_plan) >= 2:
        plan_steps = _normalize_steps(raw_plan)
        llm_params = await generate_llm_plan_params(
            ctx.message,
            plan_steps,
            model_id=model_id,
        )
    return prepare_plan_confirm_gate(
        ctx,
        model_id=model_id,
        raw_plan=raw_plan,
        llm_params=llm_params,
    )
