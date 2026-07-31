"""
P2：条件流程中间表示（Flow IR）与校验。

文件职责
--------
定义 LLM / 规则产出的窄范围 IR（任务节点 + 至多一个条件网关），
并提供白名单校验、规范化。真正落成 FlowDocument 由 ``llm_flow_compiler`` 完成。

白话解释
--------
不让模型直接画 BPMN 坐标；只让它说出「查谁、什么条件、then/else 各干什么」，
服务端再确定性编译成可执行画布，避免非法边 / 缺 else。
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

# MVP：条件左值允许的字段名（无 steps. 前缀时亦可）
ALLOWED_CONDITION_FIELDS: frozenset[str] = frozenset({"onlineStatus"})

ALLOWED_OPERATORS: frozenset[str] = frozenset(
    {
        "eq",
        "ne",
        "contains",
        "not_contains",
        "gt",
        "gte",
        "lt",
        "lte",
        "exists",
        "not_exists",
    }
)

_STEPS_FIELD_RE = re.compile(r"^steps\.([A-Za-z0-9_\-]+)\.([A-Za-z0-9_]+)$")

# 各工具允许写入 params_by_tool 的键（防 LLM 塞入无关字段）
_TOOL_ARG_ALLOWLIST: dict[str, frozenset[str]] = {
    "get_device_detail": frozenset({"device_code", "device_name"}),
    "send_device_cmd": frozenset(
        {
            "device_code",
            "device_name",
            "action",
            "variable_name",
            "variable_value",
            "operate_name",
        }
    ),
    "query_device_variables": frozenset({"device_code", "device_name", "var_name"}),
    "query_devices": frozenset({"search", "device_name", "device_code", "online_status"}),
    "open_device_detail": frozenset({"device_code", "device_name"}),
}

_LEADING_QUERY_VERB_RE = re.compile(
    r"^(?:查看|查询|先查|查一下|查下|查)\s*",
)


def sanitize_flow_ir_node_args(tool: str, raw: dict[str, Any] | None) -> dict[str, Any]:
    """按工具白名单清洗 IR.args，并去掉 device_name 前误带的「查看/查」。"""
    allowed = _TOOL_ARG_ALLOWLIST.get(tool)
    if not allowed or not isinstance(raw, dict):
        return {}
    cleaned: dict[str, Any] = {}
    for key, value in raw.items():
        if key not in allowed:
            continue
        if isinstance(value, str):
            text = value.strip()
            if key == "device_name":
                text = _LEADING_QUERY_VERB_RE.sub("", text).strip()
            if not text:
                continue
            cleaned[key] = text
        elif value is not None and value != "":
            cleaned[key] = value
    return cleaned


def flow_ir_to_params_by_tool(ir: FlowIr) -> dict[str, dict[str, Any]]:
    """从 IR 节点 args 汇总 params_by_tool（同工具后者覆盖前者非空键）。"""
    params_by_tool: dict[str, dict[str, Any]] = {}
    for node in ir.nodes:
        tool = (node.tool or "").strip()
        if not tool:
            continue
        cleaned = sanitize_flow_ir_node_args(tool, node.args)
        if not cleaned:
            continue
        base = dict(params_by_tool.get(tool) or {})
        base.update(cleaned)
        params_by_tool[tool] = base
    return params_by_tool


class FlowIrTaskNode(BaseModel):
    """IR 任务节点（将编译为 AUTO）。"""

    id: str = Field(description="节点 id，如 step_query")
    tool: str = Field(description="catalog 已注册工具名")
    label: str = Field(description="使用者视角步骤描述")
    # 槽位由 LLM 填写（如 device_name / action），禁止依赖服务端正则猜设备名
    args: dict[str, Any] = Field(
        default_factory=dict,
        description="工具入参，如 {device_name, action, device_code}",
    )

    @field_validator("id", "tool", "label", mode="before")
    @classmethod
    def _strip_str(cls, value: Any) -> str:
        return str(value or "").strip()

    @field_validator("args", mode="before")
    @classmethod
    def _coerce_args(cls, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            return {}
        return dict(value)


class FlowIrCondition(BaseModel):
    """IR 条件网关（P2：至多一条，编译为 if + else）。"""

    id: str = Field(description="条件节点 id，如 cond_online")
    label: str = Field(default="条件", description="条件节点标题")
    left: str = Field(description="左值字段，如 onlineStatus 或 steps.step_query.onlineStatus")
    operator: Literal[
        "eq",
        "ne",
        "contains",
        "not_contains",
        "gt",
        "gte",
        "lt",
        "lte",
        "exists",
        "not_exists",
    ] = Field(description="比较运算符")
    right: str | int | float | bool | None = Field(
        default=None,
        description="右值；exists/not_exists 可省略",
    )
    then_target: str = Field(description="条件命中时的首任务节点 id")
    else_target: str = Field(description="else 分支首任务节点 id")

    @field_validator("id", "label", "left", "then_target", "else_target", mode="before")
    @classmethod
    def _strip_str(cls, value: Any) -> str:
        return str(value or "").strip()


class FlowIr(BaseModel):
    """条件流程 IR：entry + 任务节点 + 至多一个条件。"""

    entry: str = Field(description="start 之后第一个任务节点 id")
    nodes: list[FlowIrTaskNode] = Field(default_factory=list, max_length=8)
    conditions: list[FlowIrCondition] = Field(default_factory=list, max_length=1)

    @field_validator("entry", mode="before")
    @classmethod
    def _strip_entry(cls, value: Any) -> str:
        return str(value or "").strip()


def extract_condition_field_name(left: str) -> str | None:
    """从 left 表达式提取字段名；非法路径返回 None。"""
    text = (left or "").strip()
    if not text:
        return None
    if text in ALLOWED_CONDITION_FIELDS:
        return text
    matched = _STEPS_FIELD_RE.match(text)
    if matched:
        field = matched.group(2)
        return field if field in ALLOWED_CONDITION_FIELDS else None
    # 禁止 $. / globals. 等未约定路径进入 MVP
    return None


def _allowed_tool_names() -> frozenset[str]:
    from platform_mcp.runtime.tool_catalog_loader import load_tool_catalog

    return frozenset(str(t["name"]) for t in load_tool_catalog() if t.get("name"))


def normalize_and_validate_flow_ir(ir: FlowIr) -> FlowIr:
    """
    校验并规范化 FlowIr。

    失败时抛 ValueError（调用方应捕获并回退 D1）。
    """
    if not ir.entry:
        raise ValueError("IR entry 不能为空")
    if not ir.nodes:
        raise ValueError("IR nodes 不能为空")
    if len(ir.conditions) > 1:
        raise ValueError("P2 仅支持至多一个条件网关")

    allowed_tools = _allowed_tool_names()
    node_ids: set[str] = set()
    normalized_nodes: list[FlowIrTaskNode] = []
    for node in ir.nodes:
        if not node.id:
            raise ValueError("任务节点 id 不能为空")
        if node.id in node_ids:
            raise ValueError(f"重复节点 id: {node.id}")
        node_ids.add(node.id)
        if node.tool not in allowed_tools:
            raise ValueError(f"未知工具: {node.tool}")
        cleaned_args = sanitize_flow_ir_node_args(node.tool, node.args)
        normalized_nodes.append(
            node.model_copy(
                update={
                    "label": node.label or node.tool,
                    "args": cleaned_args,
                }
            )
        )

    if ir.entry not in node_ids:
        raise ValueError(f"entry 不在 nodes 中: {ir.entry}")

    if not ir.conditions:
        raise ValueError("条件 IR 须包含至少一条 condition")

    cond = ir.conditions[0]
    if not cond.id:
        raise ValueError("条件节点 id 不能为空")
    if cond.id in node_ids:
        raise ValueError(f"条件节点 id 与任务 id 冲突: {cond.id}")
    if extract_condition_field_name(cond.left) is None:
        raise ValueError(f"条件 left 不在白名单: {cond.left}")
    if cond.operator not in ALLOWED_OPERATORS:
        raise ValueError(f"不支持的运算符: {cond.operator}")
    if cond.then_target not in node_ids:
        raise ValueError(f"then_target 不在 nodes 中: {cond.then_target}")
    if cond.else_target not in node_ids:
        raise ValueError(f"else_target 不在 nodes 中: {cond.else_target}")
    if cond.then_target == cond.else_target:
        raise ValueError("then_target 与 else_target 不能相同")

    field = extract_condition_field_name(cond.left)
    assert field is not None
    left = cond.left.strip()
    if left in ALLOWED_CONDITION_FIELDS:
        left = f"steps.{ir.entry}.{field}"

    normalized_cond = cond.model_copy(update={"left": left, "label": cond.label or "条件"})
    return FlowIr(
        entry=ir.entry,
        nodes=normalized_nodes,
        conditions=[normalized_cond],
    )
