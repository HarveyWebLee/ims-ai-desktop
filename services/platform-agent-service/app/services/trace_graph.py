"""
Phase D3：从 Trace 事件序列构建执行图（节点/边/Mermaid）。

文件职责
--------
把一轮 run 里 TraceCollector 记下的 events[] 转成「有向图」：
nodes / edges，并附一份 Mermaid flowchart 源码，方便只读可视化。

一次 run 的链路（白话）
----------------------
TraceCollector 拍好的「镜头列表」进来之后：

  events[0]=用户输入 → events[1]=计划 → events[2]=工具开始 → …
    → build_trace_graph：插一个「开始」节点，再按时间依次连边
    → enrich_trace_run：给 API 返回附上 graph + plan_snapshot

前端拿到 graph.nodes/edges 或 mermaid 就能画出「这一场短片怎么走的」。

在 Agent 流程中的位置
--------------------
Trace 查询只读后处理（不写 store）：
  GET /traces → trace_store.get_run → enrich_trace_run → 响应 JSON

如何被调用
----------
- Trace API 组装响应：``enrich_trace_run(run)``
- 需要单独构图：``build_trace_graph(events)``
"""

from __future__ import annotations

from typing import Any

# kind → 展示样式类（前端 traceTagUtils 可复用）
_KIND_STYLE: dict[str, str] = {
    "user_message": "traceUser",
    "plan": "tracePlan",
    "replan": "traceReplan",
    "tool_start": "traceTool",
    "tool_end": "traceTool",
    "interrupt": "traceHitl",
    "client_action": "traceClient",
    "error": "traceError",
    "done": "traceDone",
}


def _node_style(kind: str) -> str:
    """事件 kind 映射为前端 CSS/标签样式名；未知 kind 走默认。"""
    return _KIND_STYLE.get(kind, "traceDefault")


def build_trace_graph(events: list[dict[str, Any]]) -> dict[str, Any]:
    """
    将 TraceCollector 事件列表转为有向图结构。

    构图规则（白话）:
        永远先有「开始」节点，然后按 events 顺序一字排开，相邻镜头连一条边。
        这不是状态机拓扑，而是「时间线 → 折线图」的简单串。

    返回:
        nodes: [{id, label, kind, style, ts}]
        edges: [{from, to}]
        mermaid: Mermaid flowchart 源码（只读）
    """
    if not events:
        return {"nodes": [], "edges": [], "mermaid": "flowchart LR\n  empty[无 Trace 事件]"}

    nodes: list[dict[str, Any]] = [
        {
            "id": "__start__",
            "label": "开始",
            "kind": "start",
            "style": "traceStart",
            "ts": events[0].get("ts"),
        }
    ]
    edges: list[dict[str, str]] = []
    prev_id = "__start__"
    mermaid_lines = ["flowchart TD", "  __start__([开始])"]

    for i, evt in enumerate(events):
        evt_id = str(evt.get("id") or f"evt-{i}")
        kind = str(evt.get("kind") or "unknown")
        label = str(evt.get("label") or kind)[:40]
        # Mermaid 节点文案不能含未转义双引号
        safe_label = label.replace('"', "'")
        nodes.append(
            {
                "id": evt_id,
                "label": label,
                "kind": kind,
                "style": _node_style(kind),
                "ts": evt.get("ts"),
            }
        )
        edges.append({"from": prev_id, "to": evt_id})
        node_shape = f'  {evt_id}["{safe_label}"]'
        mermaid_lines.append(node_shape)
        mermaid_lines.append(f"  {prev_id} --> {evt_id}")
        prev_id = evt_id

    return {
        "nodes": nodes,
        "edges": edges,
        "mermaid": "\n".join(mermaid_lines),
    }


def enrich_trace_run(run: dict[str, Any]) -> dict[str, Any]:
    """
    为 trace run 附加 graph 与 plan_snapshot 字段（不修改原 dict，返回新副本）。

    plan_snapshot:
        优先用持久化字段；否则从时间线上「最后一次 plan 事件」的 detail 反推，
        方便旧数据也能在 UI 看到当时任务步骤。
    """
    events = run.get("events")
    if not isinstance(events, list):
        base = {**run, "graph": build_trace_graph([])}
    else:
        base = {**run, "graph": build_trace_graph(events)}
    # plan_snapshot：优先 trace 持久化字段，否则从 plan 事件 detail 推导
    snapshot = run.get("plan_snapshot")
    if not isinstance(snapshot, dict):
        for evt in reversed(events or []):
            if evt.get("kind") == "plan" and isinstance(evt.get("detail"), dict):
                detail = evt["detail"]
                snapshot = {"steps": detail.get("steps") or []}
                if isinstance(detail.get("graph"), dict):
                    snapshot["graph"] = detail["graph"]
                break
    if isinstance(snapshot, dict):
        base["plan_snapshot"] = snapshot
    return base
