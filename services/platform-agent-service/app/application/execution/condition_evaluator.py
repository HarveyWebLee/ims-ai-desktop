"""BPMN 条件表达式求值（P1：字段比较子集）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ConditionRule:
    """单条可执行条件规则。"""

    key: str
    left: str
    operator: str
    right: Any = None
    label: str | None = None


def normalize_operator(operator: str) -> str:
    """将画布运算符归一为执行器内部名。"""
    op = str(operator or "").strip().lower()
    aliases = {
        "neq": "ne",
        "not_contains": "not_contains",
        "is_empty": "not_exists",
        "is_not_empty": "exists",
    }
    return aliases.get(op, op)


def _coerce_compare(left: Any, right: Any) -> tuple[Any, Any]:
    """数字与字符串比较时尝试统一类型。"""
    if isinstance(left, (int, float)) and isinstance(right, str):
        try:
            if "." in right:
                return left, float(right)
            return left, int(right)
        except ValueError:
            return left, right
    if isinstance(left, str) and isinstance(right, (int, float)):
        return left, str(right)
    return left, right


def evaluate_operator(left: Any, operator: str, right: Any = None) -> bool:
    """
    对左右值执行比较。

    P1 支持：eq / ne / contains / not_contains / gt / gte / lt / lte / exists / not_exists
    """
    op = normalize_operator(operator)
    if op == "exists":
        if left is None:
            return False
        if isinstance(left, str):
            return bool(left.strip())
        if isinstance(left, (list, dict, tuple, set)):
            return len(left) > 0
        return True
    if op == "not_exists":
        return not evaluate_operator(left, "exists")

    left_cmp, right_cmp = _coerce_compare(left, right)

    if op == "eq":
        return left_cmp == right_cmp
    if op == "ne":
        return left_cmp != right_cmp
    if op == "contains":
        if left_cmp is None:
            return False
        return str(right_cmp) in str(left_cmp)
    if op == "not_contains":
        if left_cmp is None:
            return True
        return str(right_cmp) not in str(left_cmp)
    if op == "gt":
        return left_cmp is not None and right_cmp is not None and left_cmp > right_cmp
    if op == "gte":
        return left_cmp is not None and right_cmp is not None and left_cmp >= right_cmp
    if op == "lt":
        return left_cmp is not None and right_cmp is not None and left_cmp < right_cmp
    if op == "lte":
        return left_cmp is not None and right_cmp is not None and left_cmp <= right_cmp
    return False


def _extract_flow_value(field: Any) -> Any:
    """解析 Flowgram ConditionRow 的 left/right 结构。"""
    if field is None:
        return None
    if isinstance(field, (str, int, float, bool)):
        return field
    if isinstance(field, dict):
        if "content" in field:
            return field.get("content")
        if "value" in field:
            return _extract_flow_value(field.get("value"))
    return field


def parse_condition_item(item: dict[str, Any]) -> ConditionRule | None:
    """
    从 CONDITION 节点 conditions[] 项解析规则。

    支持两种形态：
    1. 扁平：{ key, left, operator, right, label }
    2. Flowgram：{ key, value: { left, operator, right } }
    """
    if not isinstance(item, dict):
        return None
    key = str(item.get("key") or "").strip()
    if not key:
        return None

    if item.get("left") and item.get("operator"):
        return ConditionRule(
            key=key,
            left=str(item.get("left") or ""),
            operator=str(item.get("operator") or ""),
            right=item.get("right"),
            label=item.get("label"),
        )

    value = item.get("value")
    if not isinstance(value, dict):
        return None

    left_raw = value.get("left")
    right_raw = value.get("right")
    left = _extract_flow_value(left_raw)
    right = _extract_flow_value(right_raw)
    if left is None and isinstance(left_raw, dict):
        left = str(left_raw.get("content") or "")
    if isinstance(left, dict):
        left = str(left.get("content") or "")
    operator = str(value.get("operator") or value.get("op") or "").strip()
    if not left or not operator:
        return None
    return ConditionRule(
        key=key,
        left=str(left),
        operator=operator,
        right=right,
        label=item.get("label"),
    )


def resolve_condition_left(
    rule: ConditionRule,
    *,
    last_task_node_id: str | None,
) -> str:
    """
    补全条件左值路径。

    若 left 为字段名（无 steps. 前缀），默认引用最近任务节点：
    onlineStatus → steps.{last_task_node_id}.onlineStatus
    """
    left = rule.left.strip()
    if left.startswith("steps.") or left.startswith("globals.") or left.startswith("$."):
        return left
    if last_task_node_id:
        return f"steps.{last_task_node_id}.{left}"
    return left


def evaluate_condition_rules(
    rules: list[ConditionRule],
    get_value: Any,
    *,
    last_task_node_id: str | None = None,
) -> tuple[str | None, str | None]:
    """
      按顺序匹配条件，返回 (matched_key, error)。

      全部不匹配时返回 ("else", None) 表示应走 else 支。
    若无规则可匹配且无 else 语义，返回 (None, error_msg)。
    """
    for rule in rules:
        left_expr = resolve_condition_left(rule, last_task_node_id=last_task_node_id)
        left_val = get_value(left_expr)
        if evaluate_operator(left_val, rule.operator, rule.right):
            return rule.key, None
    return "else", None
