"""BPMN 图执行上下文：节点输出、运行时状态与表达式取值。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


def _get_nested(data: Any, path: str) -> Any:
    """按点分路径读取嵌套字段，如 onlineStatus 或 data.status。"""
    if not path:
        return data
    current = data
    for part in path.split("."):
        if not part:
            continue
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


@dataclass
class NodeRuntime:
    """单节点运行时快照。"""

    node_id: str
    node_type: str
    status: str = "pending"
    skip_reason: str | None = None
    matched_branch_key: str | None = None


@dataclass
class ExecutionContext:
    """
    BPMN 图执行上下文。

    - outputs: 各任务节点工具结果（解析后的 dict）
    - node_runtimes: 全图节点状态（含 CONDITION / skipped）
    - last_task_node_id: 最近成功完成的任务节点，供条件默认引用
    """

    thread_id: str = ""
    user_message: str = ""
    globals: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    node_runtimes: dict[str, NodeRuntime] = field(default_factory=dict)
    last_task_node_id: str | None = None

    def ensure_runtime(self, node_id: str, node_type: str) -> NodeRuntime:
        """获取或初始化节点运行时。"""
        runtime = self.node_runtimes.get(node_id)
        if runtime is None:
            runtime = NodeRuntime(node_id=node_id, node_type=node_type)
            self.node_runtimes[node_id] = runtime
        return runtime

    def set_node_output(self, node_id: str, raw_result: str) -> dict[str, Any]:
        """解析工具 JSON 结果并写入 outputs。"""
        parsed: Any
        try:
            parsed = json.loads(raw_result)
        except json.JSONDecodeError, TypeError:
            parsed = {"raw": str(raw_result)}
        if not isinstance(parsed, dict):
            parsed = {"value": parsed}
        self.outputs[node_id] = parsed
        data_block = parsed.get("data")
        if isinstance(data_block, dict):
            promoted = dict(parsed)
            for key in ("onlineStatus", "ok", "summary"):
                if key in data_block and key not in promoted:
                    promoted[key] = data_block[key]
            self.outputs[node_id] = promoted
            return promoted
        return parsed

    def get_path(self, expr: str) -> Any:
        """
        按表达式取值。

        支持：
        - steps.{node_id}.{field...}
        - globals.{field...} 或 $.{field...}
        """
        text = str(expr or "").strip()
        if not text:
            return None
        if text.startswith("steps."):
            parts = text.split(".", 2)
            if len(parts) < 3:
                return None
            node_id = parts[1]
            field_path = parts[2]
            return _get_nested(self.outputs.get(node_id), field_path)
        if text.startswith("globals."):
            return _get_nested(self.globals, text[len("globals.") :])
        if text.startswith("$."):
            return _get_nested(self.globals, text[2:])
        return _get_nested(self.globals, text)

    def mark_node(
        self,
        node_id: str,
        node_type: str,
        status: str,
        *,
        skip_reason: str | None = None,
        matched_branch_key: str | None = None,
    ) -> None:
        """更新节点运行时状态。"""
        runtime = self.ensure_runtime(node_id, node_type)
        runtime.status = status
        if skip_reason is not None:
            runtime.skip_reason = skip_reason
        if matched_branch_key is not None:
            runtime.matched_branch_key = matched_branch_key
        if status == "done" and node_type in ("AUTO", "MANUAL", "LLM"):
            self.last_task_node_id = node_id

    def to_state_dict(self) -> dict[str, Any]:
        """序列化为 session 持久化结构（迭代 2 使用）。"""
        return {
            "thread_id": self.thread_id,
            "user_message": self.user_message,
            "globals": dict(self.globals),
            "outputs": dict(self.outputs),
            "last_task_node_id": self.last_task_node_id,
            "node_runtimes": {
                node_id: {
                    "node_id": rt.node_id,
                    "node_type": rt.node_type,
                    "status": rt.status,
                    "skip_reason": rt.skip_reason,
                    "matched_branch_key": rt.matched_branch_key,
                }
                for node_id, rt in self.node_runtimes.items()
            },
        }

    @classmethod
    def from_state_dict(cls, data: dict[str, Any]) -> ExecutionContext:
        """从持久化结构恢复上下文。"""
        ctx = cls(
            thread_id=str(data.get("thread_id") or ""),
            user_message=str(data.get("user_message") or ""),
            globals=dict(data.get("globals") or {}),
            outputs=dict(data.get("outputs") or {}),
            last_task_node_id=data.get("last_task_node_id"),
        )
        for node_id, raw in (data.get("node_runtimes") or {}).items():
            if not isinstance(raw, dict):
                continue
            ctx.node_runtimes[str(node_id)] = NodeRuntime(
                node_id=str(raw.get("node_id") or node_id),
                node_type=str(raw.get("node_type") or ""),
                status=str(raw.get("status") or "pending"),
                skip_reason=raw.get("skip_reason"),
                matched_branch_key=raw.get("matched_branch_key"),
            )
        return ctx
