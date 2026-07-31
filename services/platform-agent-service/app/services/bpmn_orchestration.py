"""
BPMN 级流程编排服务（Plan ↔ 画布 JSON 互操作；桌面端 M1 可不消费 UI）。

文件职责
--------
在「Agent Plan 步骤」与「BPMN 画布 FlowDocument」之间做双向转换、结构校验，
以及用户在画布上改步骤后的合并；并组装线程级 ``bpmn_snapshot`` 供持久化 / API。

说明：线性 Plan 执行走 ``execute_plan_steps``；含条件网关的图执行走 ``BpmnExecutor``（``execute_bpmn_graph``）。
画布是「看得见的 Plan 编辑器」；条件分支执行见 ``app.application.execution.bpmn_executor``。

在 Agent 流程中的位置
--------------------
    plan_confirm interrupt
      → plan_steps_to_flow_document(steps) 嵌入 SSE
    前端 BpmnFlowgram 编辑后
      → POST /bpmn/convert、/bpmn/validate
      → flow_document_to_plan_steps / validate_flow_document
    用户批准（可能含 skipped）
      → merge_bpmn_steps_with_previous → 正式执行

如何被调用
----------
- API：``app.api.bpmn``（convert / validate / threads bpmn）
- 服务：``plan_confirm.prepare_plan_confirm_gate``；BPMN 快照经 ``session_store`` / ParentState
- 依赖：``plan_graph.build_plan_sse_payload`` 拼 graph + flow_document
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.services.plan_graph import build_plan_sse_payload

# 与前端 BpmnFlowgram nodes/constants.ts 对齐的任务节点类型
_TASK_NODE_TYPES = frozenset({"AUTO", "MANUAL", "LLM"})
# Plan 编排须绑定 Agent catalog 工具名的节点（不含 LLM 占位节点）
_TOOL_BINDING_NODE_TYPES = frozenset({"AUTO", "MANUAL"})
_START_TYPE = "start"
_END_TYPE = "end"
_CONDITION_TYPE = "CONDITION"

# 线性布局：每步水平间距与起点坐标（仅影响画布美观，不影响执行）
_HORIZONTAL_GAP = 420
_BASE_X = 180
_BASE_Y = 0


@lru_cache(maxsize=1)
def _enabled_tool_names() -> frozenset[str]:
    """读取已启用工具名集合（来自 tool catalog）。"""
    from platform_mcp.runtime.tool_catalog_loader import load_tool_catalog

    return frozenset(
        str(tool.get("name") or "")
        for tool in load_tool_catalog()
        if str(tool.get("name") or "").strip()
    )


def plan_steps_to_flow_document(steps: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Plan 步骤列表 → BPMN 画布 JSON。

    白话解释
    --------
    固定生成一条直线：开始 → 各任务节点 → 结束。
    处于 HITL / 待确认状态的步骤画成 MANUAL，其余为 AUTO。

    参数
    ----
    steps : list[dict]
        Agent Plan 步骤（id / label / tool / status）。

    返回
    ----
    dict
        含 ``nodes``、``edges``、``globalVariable``，与前端 FlowDocument 对齐。
    """
    nodes: list[dict[str, Any]] = [
        {
            "id": "start_0",
            "type": _START_TYPE,
            "meta": {"position": {"x": _BASE_X, "y": _BASE_Y}},
            "data": {
                "title": "开始事件",
                "outputs": {"type": "object", "properties": {}, "required": []},
            },
        }
    ]
    edges: list[dict[str, Any]] = []
    prev_id = "start_0"

    for index, step in enumerate(steps):
        node_id = str(step.get("id") or f"step_{index}")
        status = str(step.get("status") or "pending")
        model_id = step.get("modelId")
        tool = step.get("tool")
        # 有 modelId 且无 tool → LLM 编排节点；HITL → MANUAL；其余 AUTO
        is_llm = bool(model_id) and not tool
        is_hitl = (not is_llm) and status in ("awaiting_hitl", "awaiting_confirm")
        if is_llm:
            node_type = "LLM"
        elif is_hitl:
            node_type = "MANUAL"
        else:
            node_type = "AUTO"
        data: dict[str, Any] = {
            "title": step.get("label") or tool or model_id or node_id,
            "tool": tool,
            "planStatus": status,
        }
        if model_id:
            data["modelId"] = model_id
        if step.get("side") is not None:
            data["side"] = step.get("side")
        if step.get("riskLevel") is not None:
            data["riskLevel"] = step.get("riskLevel")
        if is_llm:
            data["temperature"] = step.get("temperature", 0.5)
        nodes.append(
            {
                "id": node_id,
                "type": node_type,
                "meta": {
                    "position": {
                        "x": _BASE_X + (index + 1) * _HORIZONTAL_GAP,
                        "y": _BASE_Y,
                    }
                },
                "data": data,
            }
        )
        edges.append({"sourceNodeID": prev_id, "targetNodeID": node_id})
        prev_id = node_id

    end_id = "end_0"
    nodes.append(
        {
            "id": end_id,
            "type": _END_TYPE,
            "meta": {
                "position": {
                    "x": _BASE_X + (len(steps) + 1) * _HORIZONTAL_GAP,
                    "y": _BASE_Y,
                }
            },
            "data": {"title": "结束事件"},
        }
    )
    edges.append({"sourceNodeID": prev_id, "targetNodeID": end_id})

    return {
        "nodes": nodes,
        "edges": edges,
        "globalVariable": {"type": "object", "required": [], "properties": {}},
    }


def _condition_gateway_errors(doc: dict[str, Any]) -> list[str]:
    """条件排他网关校验：出度 ≤2；双分支须含 else 出口（与 validate / convert 共用）。"""
    errors: list[str] = []
    nodes = doc.get("nodes")
    edges = doc.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return errors
    out_degree: dict[str, int] = {}
    out_edges_by_src: dict[str, list[dict[str, Any]]] = {}
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        src = str(edge.get("sourceNodeID") or "")
        if not src:
            continue
        out_degree[src] = out_degree.get(src, 0) + 1
        out_edges_by_src.setdefault(src, []).append(edge)
    for node in nodes:
        if not isinstance(node, dict) or node.get("type") != _CONDITION_TYPE:
            continue
        node_id = str(node.get("id") or "")
        degree = out_degree.get(node_id, 0)
        title = str((node.get("data") or {}).get("title") or node_id or "条件节点")
        if degree > 2:
            errors.append(f"条件节点「{title}」出边超过 2 条，当前仅支持 if + else 双分支")
            continue
        if degree == 2:
            outgoing = out_edges_by_src.get(node_id, [])
            has_else = any(str(e.get("sourcePortID") or "") == "else" for e in outgoing)
            if not has_else:
                errors.append(f"条件节点「{title}」双分支须包含 else 出口")
    return errors


# 兼容旧引用
_condition_multi_branch_errors = _condition_gateway_errors


def _node_data(node: dict[str, Any]) -> dict[str, Any]:
    """安全取出节点 data（保证为 dict[str, Any]）。"""
    raw = node.get("data")
    if not isinstance(raw, dict):
        return {}
    return {str(k): v for k, v in raw.items()}


def _node_to_plan_step(node: dict[str, Any]) -> dict[str, Any]:
    data = _node_data(node)
    step: dict[str, Any] = {
        "id": str(node.get("id")),
        "label": str(data.get("title") or node.get("id")),
        "tool": data.get("tool"),
        "status": str(data.get("planStatus") or "pending"),
    }
    if data.get("modelId") is not None:
        step["modelId"] = data.get("modelId")
    if data.get("side") is not None:
        step["side"] = data.get("side")
    if data.get("riskLevel") is not None:
        step["riskLevel"] = data.get("riskLevel")
    return step


def flow_document_to_plan_steps(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """
    BPMN 画布 JSON → Plan 步骤列表。

    算法（白话）
    ------------
    1. 取出 AUTO/MANUAL/LLM 任务节点
    2. 从 start 沿边往后走，按拓扑顺序收集任务
    3. 走不通时：退回按任务节点原始顺序（防坏画布）

    含条件双分支时按 BFS 收集全部可达任务节点（与 validate 一致，防止静默丢支）。
    """
    branch_errors = _condition_gateway_errors(doc)
    if branch_errors:
        raise ValueError(branch_errors[0])

    nodes = doc.get("nodes")
    edges = doc.get("edges")
    if not isinstance(nodes, list):
        return []

    task_nodes = [n for n in nodes if isinstance(n, dict) and n.get("type") in _TASK_NODE_TYPES]
    if not task_nodes:
        return []

    out_edges_map: dict[str, list[str]] = {}
    if isinstance(edges, list):
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            src = edge.get("sourceNodeID")
            tgt = edge.get("targetNodeID")
            if src and tgt:
                out_edges_map.setdefault(str(src), []).append(str(tgt))

    start_node = next((n for n in nodes if n.get("type") == _START_TYPE), None)
    node_by_id = {str(n.get("id")): n for n in nodes if n.get("id")}
    ordered: list[dict[str, Any]] = []
    seen: set[str] = set()
    queue: list[str] = []
    if start_node and start_node.get("id"):
        queue.append(str(start_node.get("id")))
    elif task_nodes:
        queue.append(str(task_nodes[0].get("id")))

    while queue:
        cursor = queue.pop(0)
        if cursor in seen:
            continue
        seen.add(cursor)
        node = node_by_id.get(cursor)
        if not node:
            continue
        node_type = node.get("type")
        if node_type in _TASK_NODE_TYPES:
            ordered.append(_node_to_plan_step(node))
        if node_type == _END_TYPE:
            continue
        for next_id in out_edges_map.get(cursor, []):
            queue.append(next_id)

    if ordered:
        return ordered

    return [_node_to_plan_step(n) for n in task_nodes]


def merge_bpmn_steps_with_previous(
    extracted: list[dict[str, Any]],
    previous: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    合并 BPMN 新提取步骤与批准前的既有 Plan。

    白话解释
    --------
    用户在画布上可能只改标题/顺序，或把某步标成 skipped。
    合并时：同 id 尽量保留已有 skipped；新出现的步默认 awaiting_confirm。

    参数
    ----
    extracted :
        从最新 flow_document 抽出的步骤。
    previous :
        门控前已生成的计划步骤。

    返回
    ----
    list[dict]
        合并后的步骤列表（供 resume 执行）。
    """
    prev_by_id = {str(s.get("id")): s for s in previous if s.get("id")}
    merged: list[dict[str, Any]] = []
    for step in extracted:
        step_id = str(step.get("id"))
        prev = prev_by_id.get(step_id)
        if not prev:
            status = str(step.get("status") or "pending")
            merged.append(
                {
                    **step,
                    "status": "skipped" if status == "skipped" else "awaiting_confirm",
                }
            )
            continue
        # 同 id：画布侧 label/tool 优先，但 previous.skipped 不可被轻易冲掉；保留执行摘要字段
        merged.append(
            {
                **prev,
                **step,
                "label": step.get("label") or prev.get("label"),
                "tool": step.get("tool") if step.get("tool") is not None else prev.get("tool"),
                "status": "skipped" if str(prev.get("status")) == "skipped" else step.get("status"),
                "args": step.get("args") if step.get("args") is not None else prev.get("args"),
                "resultSummary": step.get("resultSummary")
                if step.get("resultSummary") is not None
                else prev.get("resultSummary"),
                "errorMessage": step.get("errorMessage")
                if step.get("errorMessage") is not None
                else prev.get("errorMessage"),
                "startedAt": step.get("startedAt")
                if step.get("startedAt") is not None
                else prev.get("startedAt"),
                "endedAt": step.get("endedAt")
                if step.get("endedAt") is not None
                else prev.get("endedAt"),
                "side": step.get("side") if step.get("side") is not None else prev.get("side"),
                "riskLevel": step.get("riskLevel")
                if step.get("riskLevel") is not None
                else prev.get("riskLevel"),
                "hitl": step.get("hitl") if step.get("hitl") is not None else prev.get("hitl"),
                "retry": step.get("retry") if step.get("retry") is not None else prev.get("retry"),
                "attempt": step.get("attempt")
                if step.get("attempt") is not None
                else prev.get("attempt"),
                "autoRetryFrom": step.get("autoRetryFrom")
                if step.get("autoRetryFrom") is not None
                else prev.get("autoRetryFrom"),
                "autoRetryTo": step.get("autoRetryTo")
                if step.get("autoRetryTo") is not None
                else prev.get("autoRetryTo"),
                "modelId": step.get("modelId")
                if step.get("modelId") is not None
                else prev.get("modelId"),
            }
        )
    return merged


def count_active_plan_steps(steps: list[dict[str, Any]]) -> int:
    """统计非 skipped 的步骤数（用于「至少一步可执行」类校验）。"""
    return sum(1 for s in steps if str(s.get("status")) != "skipped")


def validate_flow_document(doc: dict[str, Any]) -> dict[str, Any]:
    """
    校验 BPMN 画布 JSON 基本结构（非业务语义全校验）。

    检查点
    ------
    - nodes 非空数组；edges 为数组
    - 至少一个 start、一个 end
    - 至少一个任务节点（AUTO/MANUAL/LLM）
    - 连线指向不存在的节点 → warnings（不直接判 invalid）

    返回
    ----
    dict
        ``{ valid: bool, errors: list[str], warnings: list[str] }``
    """
    errors: list[str] = []
    warnings: list[str] = []

    nodes = doc.get("nodes")
    edges = doc.get("edges")
    if not isinstance(nodes, list) or not nodes:
        errors.append("nodes 不能为空")
        return {"valid": False, "errors": errors, "warnings": warnings}

    if not isinstance(edges, list):
        errors.append("edges 必须为数组")
        return {"valid": False, "errors": errors, "warnings": warnings}

    start_nodes = [n for n in nodes if n.get("type") == _START_TYPE]
    end_nodes = [n for n in nodes if n.get("type") == _END_TYPE]
    if len(start_nodes) < 1:
        errors.append("缺少开始节点（type=start）")
    if len(end_nodes) < 1:
        errors.append("缺少结束节点（type=end）")

    # 先拦多分支，避免 flow_document_to_plan_steps 抛错打断其余校验
    errors.extend(_condition_multi_branch_errors({"nodes": nodes, "edges": edges}))

    task_steps: list[dict[str, Any]] = []
    if not any("多分支" in e for e in errors):
        try:
            task_steps = flow_document_to_plan_steps(doc)
        except ValueError as exc:
            errors.append(str(exc))

    if not task_steps and not any("多分支" in e for e in errors):
        errors.append("至少需要一个任务节点（AUTO/MANUAL/LLM）")
    else:
        for node in nodes:
            if not isinstance(node, dict):
                continue
            data = _node_data(node)
            title = str(data.get("title") or node.get("id") or "任务节点")
            node_type = node.get("type")
            if node_type in _TOOL_BINDING_NODE_TYPES:
                tool = str(data.get("tool") or "").strip()
                if not tool:
                    errors.append(f"任务节点「{title}」未绑定 Agent 工具（tool）")
                    continue
                if tool not in _enabled_tool_names():
                    errors.append(f"任务节点「{title}」绑定了未注册工具：{tool}")
            elif node_type == "LLM":
                model_id = str(data.get("modelId") or "").strip()
                if not model_id:
                    errors.append(f"LLM 节点「{title}」未绑定 Agent 模型（modelId）")

    node_ids = {str(n.get("id")) for n in nodes if n.get("id")}
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        src = edge.get("sourceNodeID")
        tgt = edge.get("targetNodeID")
        if src and str(src) not in node_ids:
            warnings.append(f"连线源节点不存在: {src}")
        if tgt and str(tgt) not in node_ids:
            warnings.append(f"连线目标节点不存在: {tgt}")

    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


def build_bpmn_snapshot(
    *,
    steps: list[dict[str, Any]] | None = None,
    flow_document: dict[str, Any] | None = None,
    graph: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    构造线程级 BPMN 快照（持久化 / GET state REST 返回）。

    缺啥补啥：只有 steps 则生成画布；只有画布则反推 steps；
    再交给 ``build_plan_sse_payload`` 统一挂上 graph。

    返回
    ----
    dict
        ``steps`` / ``graph`` / ``flow_document`` / ``updated_at``（调用方可再写时间戳）。
    """
    resolved_steps = steps or (flow_document_to_plan_steps(flow_document) if flow_document else [])
    resolved_doc = flow_document or (
        plan_steps_to_flow_document(resolved_steps) if resolved_steps else None
    )
    payload = build_plan_sse_payload(
        resolved_steps,
        graph=graph,
        flow_document=resolved_doc,
    )
    return {
        "steps": payload.get("steps") or [],
        "graph": payload.get("graph"),
        "flow_document": payload.get("flow_document") or resolved_doc,
        "updated_at": None,
    }
