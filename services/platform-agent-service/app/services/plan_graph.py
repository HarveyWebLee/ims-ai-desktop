"""
Phase D4：多步 Plan 图形化结构（节点链 + Mermaid）。

文件职责
--------
把 Plan 步骤列表转成前端可画的有向链图（nodes/edges）及 Mermaid 源码；
并提供 plan_confirm 批准后的步骤规范化、以及 plan SSE 统一 payload 组装。
BPMN 画布 JSON 由 ``bpmn_orchestration`` 负责；本模块只管「轻量流程图」结构。

在 Agent 流程中的位置
--------------------
    prepare_plan_confirm_gate / wrap_stream_with_plan_trace
      → build_plan_graph(steps) / build_plan_sse_payload(...)
      → SSE ``plan`` 或 interrupt.plan_confirm 内嵌 graph
    用户批准后
      → normalize_approved_plan_steps（去掉 skipped，待确认→pending）
      → execute_plan_steps

如何被调用
----------
- ``plan_confirm``、``bpmn_orchestration.build_bpmn_snapshot``
- 前端 PlanFlowChart / TaskProgress 消费 nodes、edges、mermaid
"""

from __future__ import annotations

from typing import Any

# 步骤 status → 前端样式类（与 AiAssistant Plan 样式约定对齐）
_STATUS_STYLE: dict[str, str] = {
    "pending": "planPending",
    "running": "planRunning",
    "done": "planDone",
    "error": "planError",
    "skipped": "planSkipped",
    "awaiting_confirm": "planAwaiting",
    "awaiting_hitl": "planHitl",
}


def build_plan_graph(steps: list[dict[str, Any]]) -> dict[str, Any]:
    """
    将 Plan 步骤列表转为线性有向链图。

    白话解释
    --------
    始终先画一个「开始」节点，再按步骤顺序串联；不建分支/合流
    （复杂拓扑见 BPMN 画布）。

    参数
    ----
    steps : list[dict]
        每步至少建议含 id / label / tool / status。

    返回
    ----
    dict
        nodes: ``[{id, label, tool?, status?, kind, style}]``
        edges: ``[{from, to}]``
        mermaid: Mermaid flowchart 源码字符串
    """
    if not steps:
        return {
            "nodes": [],
            "edges": [],
            "mermaid": "flowchart LR\n  empty[无计划步骤]",
        }

    nodes: list[dict[str, Any]] = [
        {
            "id": "__start__",
            "label": "开始",
            "kind": "start",
            "style": "planStart",
        }
    ]
    edges: list[dict[str, str]] = []
    prev_id = "__start__"
    mermaid_lines = ["flowchart LR", "  __start__([开始])"]

    for i, step in enumerate(steps):
        step_id = str(step.get("id") or i + 1)
        label = str(step.get("label") or step.get("tool") or step_id)[:40]
        tool = str(step.get("tool") or "")
        status = str(step.get("status") or "pending")
        # Mermaid 节点文案内双引号易破坏语法，统一换成单引号
        safe_label = label.replace('"', "'")
        style = _STATUS_STYLE.get(status, "planPending")

        nodes.append(
            {
                "id": step_id,
                "label": label,
                "tool": tool,
                "status": status,
                "kind": "plan_step",
                "style": style,
            }
        )
        edges.append({"from": prev_id, "to": step_id})
        mermaid_lines.append(f'  {step_id}["{safe_label}"]')
        mermaid_lines.append(f"  {prev_id} --> {step_id}")
        prev_id = step_id

    return {
        "nodes": nodes,
        "edges": edges,
        "mermaid": "\n".join(mermaid_lines),
    }


def normalize_approved_plan_steps(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    plan_confirm 批准后规范化步骤。

    规则
    ----
    - ``skipped``：用户在轻量编排里勾掉的步骤，直接丢弃
    - ``awaiting_confirm`` → ``pending``：门控结束，进入可执行队列
    - 其他 status 原样保留
    """
    result: list[dict[str, Any]] = []
    for step in steps:
        st = dict(step)
        status = str(st.get("status") or "pending")
        if status == "skipped":
            continue
        if status == "awaiting_confirm":
            st["status"] = "pending"
        result.append(st)
    return result


def build_plan_sse_payload(
    steps: list[dict[str, Any]],
    *,
    graph: dict[str, Any] | None = None,
    flow_document: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    构造 ``plan`` SSE 事件 payload。

    参数
    ----
    steps :
        当前 Plan 步骤列表。
    graph :
        可选预计算图；缺省时对 steps 调用 ``build_plan_graph``。
    flow_document :
        可选 BPMN 画布 JSON；传入时原样挂到 payload，供 BpmnFlowgram。

    返回
    ----
    dict
        至少含 ``steps``、``graph``；有画布时含 ``flow_document``。
    """
    payload: dict[str, Any] = {"steps": steps}
    payload["graph"] = graph if isinstance(graph, dict) else build_plan_graph(steps)
    if isinstance(flow_document, dict):
        payload["flow_document"] = flow_document
    return payload
