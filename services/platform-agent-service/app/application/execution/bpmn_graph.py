"""BPMN FlowDocument → 可执行图结构。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

_START_TYPES = frozenset({"start", "START"})
_END_TYPES = frozenset({"end", "END"})
_TASK_TYPES = frozenset({"AUTO", "MANUAL", "LLM"})
_GATEWAY_TYPES = frozenset({"CONDITION"})


@dataclass(frozen=True)
class ExecutionEdge:
    """有向边；条件分支用 source_port_id 区分出口。"""

    source_id: str
    target_id: str
    source_port_id: str | None = None


@dataclass
class ExecutionNode:
    """执行图节点。"""

    id: str
    type: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionGraph:
    """BPMN 执行图邻接结构。"""

    nodes: dict[str, ExecutionNode]
    edges_out: dict[str, list[ExecutionEdge]]
    start_id: str
    end_id: str | None = None

    def outgoing(self, node_id: str) -> list[ExecutionEdge]:
        return list(self.edges_out.get(node_id, []))

    def unique_successor(self, node_id: str) -> str | None:
        """非网关节点的唯一后继（出度必须为 1）。"""
        edges = self.outgoing(node_id)
        if len(edges) != 1:
            return None
        return edges[0].target_id

    def successor_by_port(self, node_id: str, port_key: str) -> str | None:
        """条件节点按 port key 取后继。"""
        for edge in self.outgoing(node_id):
            if str(edge.source_port_id or "") == str(port_key):
                return edge.target_id
        return None

    def unselected_branch_targets(
        self,
        node_id: str,
        matched_port_key: str,
    ) -> list[str]:
        """条件求值后，未选中分支的直接后继节点 id 列表。"""
        targets: list[str] = []
        for edge in self.outgoing(node_id):
            port = str(edge.source_port_id or "")
            if port and port != matched_port_key:
                targets.append(edge.target_id)
        return targets


def flow_document_has_executable_conditions(doc: dict[str, Any]) -> bool:
    """画布是否含可执行 CONDITION 网关（出度 > 1）。"""
    nodes = doc.get("nodes")
    edges = doc.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return False
    out_degree: dict[str, int] = {}
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        src = str(edge.get("sourceNodeID") or "")
        if src:
            out_degree[src] = out_degree.get(src, 0) + 1
    for node in nodes:
        if not isinstance(node, dict):
            continue
        if str(node.get("type") or "") in _GATEWAY_TYPES:
            node_id = str(node.get("id") or "")
            if out_degree.get(node_id, 0) > 1:
                return True
    return False


def build_execution_graph(doc: dict[str, Any]) -> ExecutionGraph:
    """
    将 FlowDocument 解析为 ExecutionGraph。

    与 flow_document_to_plan_steps 不同：保留条件多分支拓扑，不压平为线性列表。
    """
    nodes_raw = doc.get("nodes")
    edges_raw = doc.get("edges")
    if not isinstance(nodes_raw, list):
        raise ValueError("nodes 必须为数组")

    nodes: dict[str, ExecutionNode] = {}
    for raw in nodes_raw:
        if not isinstance(raw, dict):
            continue
        node_id = str(raw.get("id") or "").strip()
        if not node_id:
            continue
        node_type = str(raw.get("type") or "").strip()
        raw_data = raw.get("data")
        data: dict[str, Any] = (
            {str(k): v for k, v in raw_data.items()} if isinstance(raw_data, dict) else {}
        )
        nodes[node_id] = ExecutionNode(id=node_id, type=node_type, data=data)

    if not nodes:
        raise ValueError("nodes 不能为空")

    edges_out: dict[str, list[ExecutionEdge]] = {node_id: [] for node_id in nodes}
    if isinstance(edges_raw, list):
        for raw in edges_raw:
            if not isinstance(raw, dict):
                continue
            src = str(raw.get("sourceNodeID") or "").strip()
            tgt = str(raw.get("targetNodeID") or "").strip()
            if not src or not tgt or src not in nodes or tgt not in nodes:
                continue
            port = raw.get("sourcePortID")
            port_key = str(port) if port is not None and str(port).strip() else None
            edges_out[src].append(
                ExecutionEdge(source_id=src, target_id=tgt, source_port_id=port_key)
            )

    start_nodes = [n for n in nodes.values() if n.type in _START_TYPES]
    if not start_nodes:
        raise ValueError("缺少开始节点")
    start_id = start_nodes[0].id

    end_nodes = [n for n in nodes.values() if n.type in _END_TYPES]
    end_id = end_nodes[0].id if end_nodes else None

    return ExecutionGraph(
        nodes=nodes,
        edges_out=edges_out,
        start_id=start_id,
        end_id=end_id,
    )


def iter_linear_task_node_ids(graph: ExecutionGraph) -> list[str]:
    """
    无线性网关时的任务节点遍历序（用于与 plan_runner 对齐测试）。

    跳过 start/end/CONDITION，仅收集 AUTO/MANUAL/LLM。
    """
    ordered: list[str] = []
    cursor: str | None = graph.start_id
    visited: set[str] = set()

    while cursor and cursor not in visited:
        visited.add(cursor)
        node = graph.nodes.get(cursor)
        if node is None:
            break
        if node.type in _TASK_TYPES:
            ordered.append(node.id)
        if node.type in _END_TYPES:
            break
        if node.type in _GATEWAY_TYPES:
            break
        cursor = graph.unique_successor(cursor)
    return ordered
