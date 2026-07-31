"""
P2：LLM 条件 IR 生成 + 确定性编译为 FlowDocument。

文件职责
--------
- ``generate_flow_ir``：structured output 生成 FlowIr
- ``compile_flow_document``：IR → 合法 BPMN 画布（含 if + else）
- ``try_compile_conditional_plan``：门控一站式入口，失败返回 None（静默回退）

在 Agent 流程中的位置
--------------------
    prepare_plan_confirm_gate_async
      → try_compile_conditional_plan（双灰度 + 条件意图）
          → 成功：带 flow_document 的 plan_confirm
          → 失败：resolve_task_plan 线性 D1
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import settings
from app.services.flow_ir import (
    ALLOWED_CONDITION_FIELDS,
    FlowIr,
    FlowIrCondition,
    FlowIrTaskNode,
    normalize_and_validate_flow_ir,
)

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

# 布局常量（与前端 plan-bridge 近似，保证画布可读）
_HORIZONTAL_GAP = 420
_VERTICAL_GAP = 220
_BASE_X = 180
_BASE_Y = 0


@dataclass(frozen=True)
class CompiledConditionalPlan:
    """编译成功产物：画布 + 扁平步骤 + 工具参数（供 plan_confirm）。"""

    flow_document: dict[str, Any]
    steps: list[dict[str, Any]]
    ir: FlowIr
    params_by_tool: dict[str, dict[str, Any]]


# 条件复合意图启发：与 prompt_assembly 条件句豁免共用，避免双份正则漂移
def looks_like_conditional_intent(message: str) -> bool:
    """轻量规则：疑似「条件分支 / 先查后控」复合意图。"""
    from app.services.prompt_assembly import _is_conditional_or_inspect_then_control

    return _is_conditional_or_inspect_then_control(message)


def is_llm_flow_compile_enabled() -> bool:
    """双灰度皆开才允许 NL→IR→FlowDocument。"""
    return bool(settings.agent_bpmn_llm_compile and settings.agent_bpmn_condition_exec)


def _load_prompt() -> str:
    path = _PROMPTS_DIR / "llm_flow_ir.md"
    return path.read_text(encoding="utf-8")


def _tool_list_for_prompt() -> str:
    from platform_mcp.runtime.tool_catalog_loader import load_tool_catalog

    lines: list[str] = []
    for tool in load_tool_catalog():
        name = str(tool.get("name") or "")
        if not name:
            continue
        desc = str(tool.get("description") or "")[:60]
        lines.append(f"- `{name}`：{desc}")
    return (
        "\n".join(lines)
        if lines
        else "- get_device_detail\n- send_device_cmd\n- query_device_variables"
    )


def _field_whitelist_for_prompt() -> str:
    return "\n".join(f"- `{name}`" for name in sorted(ALLOWED_CONDITION_FIELDS))


def compile_flow_document(ir: FlowIr) -> dict[str, Any]:
    """
    将已校验的 FlowIr 编译为 FlowDocumentJSON。

    布局：start → entry → CONDITION → then(上) / else(下) → end
    """
    validated = normalize_and_validate_flow_ir(ir)
    cond = validated.conditions[0]
    node_by_id = {n.id: n for n in validated.nodes}

    nodes: list[dict[str, Any]] = [
        {
            "id": "start_0",
            "type": "start",
            "meta": {"position": {"x": _BASE_X, "y": _BASE_Y}},
            "data": {
                "title": "开始事件",
                "outputs": {"type": "object", "properties": {}, "required": []},
            },
        }
    ]
    edges: list[dict[str, Any]] = []

    # entry 查询节点
    entry = node_by_id[validated.entry]
    nodes.append(
        {
            "id": entry.id,
            "type": "AUTO",
            "meta": {
                "position": {"x": _BASE_X + _HORIZONTAL_GAP, "y": _BASE_Y},
            },
            "data": {
                "title": entry.label or entry.tool,
                "tool": entry.tool,
                "planStatus": "awaiting_confirm",
                "args": dict(entry.args or {}),
            },
        }
    )
    edges.append({"sourceNodeID": "start_0", "targetNodeID": entry.id})

    # 条件网关
    cond_x = _BASE_X + 2 * _HORIZONTAL_GAP
    then_key = "if_match"
    nodes.append(
        {
            "id": cond.id,
            "type": "CONDITION",
            "meta": {"position": {"x": cond_x, "y": _BASE_Y}},
            "data": {
                "title": cond.label or "条件",
                "conditions": [
                    {
                        "key": then_key,
                        "label": cond.label or "命中",
                        "left": cond.left,
                        "operator": cond.operator,
                        "right": cond.right,
                    }
                ],
            },
        }
    )
    edges.append({"sourceNodeID": entry.id, "targetNodeID": cond.id})

    then_node = node_by_id[cond.then_target]
    else_node = node_by_id[cond.else_target]
    branch_x = _BASE_X + 3 * _HORIZONTAL_GAP

    nodes.append(
        {
            "id": then_node.id,
            "type": "AUTO",
            "meta": {
                "position": {"x": branch_x, "y": _BASE_Y - _VERTICAL_GAP // 2},
            },
            "data": {
                "title": then_node.label or then_node.tool,
                "tool": then_node.tool,
                "planStatus": "awaiting_confirm",
                "args": dict(then_node.args or {}),
            },
        }
    )
    nodes.append(
        {
            "id": else_node.id,
            "type": "AUTO",
            "meta": {
                "position": {"x": branch_x, "y": _BASE_Y + _VERTICAL_GAP // 2},
            },
            "data": {
                "title": else_node.label or else_node.tool,
                "tool": else_node.tool,
                "planStatus": "awaiting_confirm",
                "args": dict(else_node.args or {}),
            },
        }
    )
    edges.append(
        {
            "sourceNodeID": cond.id,
            "targetNodeID": then_node.id,
            "sourcePortID": then_key,
        }
    )
    edges.append(
        {
            "sourceNodeID": cond.id,
            "targetNodeID": else_node.id,
            "sourcePortID": "else",
        }
    )

    end_id = "end_0"
    end_x = _BASE_X + 4 * _HORIZONTAL_GAP
    nodes.append(
        {
            "id": end_id,
            "type": "end",
            "meta": {"position": {"x": end_x, "y": _BASE_Y}},
            "data": {"title": "结束事件"},
        }
    )
    edges.append({"sourceNodeID": then_node.id, "targetNodeID": end_id})
    edges.append({"sourceNodeID": else_node.id, "targetNodeID": end_id})

    return {
        "nodes": nodes,
        "edges": edges,
        "globalVariable": {"type": "object", "required": [], "properties": {}},
    }


def flow_ir_to_plan_steps(ir: FlowIr) -> list[dict[str, Any]]:
    """从 IR 生成扁平 steps（entry → then → else，供 TaskProgress）。"""
    validated = normalize_and_validate_flow_ir(ir)
    cond = validated.conditions[0]
    ordered_ids = [validated.entry, cond.then_target, cond.else_target]
    by_id = {n.id: n for n in validated.nodes}
    steps: list[dict[str, Any]] = []
    seen: set[str] = set()
    for nid in ordered_ids:
        if nid in seen:
            continue
        seen.add(nid)
        node = by_id[nid]
        steps.append(
            {
                "id": node.id,
                "label": (node.label or node.tool)[:48],
                "tool": node.tool,
                "status": "awaiting_confirm",
                "nodeId": node.id,
            }
        )
    return steps


def _extract_json_object(text: str) -> dict[str, Any]:
    """从模型纯文本中提取首个 JSON 对象（兼容 fence / thinking / 单引号 dict）。"""
    import ast
    import json
    import re

    raw = (text or "").strip()
    if not raw:
        raise ValueError("空响应")
    # DeepSeek thinking 等可能夹带私有标签
    raw = re.sub(r"<think>[\s\S]*?</think>", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"<reasoning>[\s\S]*?</reasoning>", "", raw, flags=re.IGNORECASE)
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw, re.IGNORECASE)
    if fence:
        raw = fence.group(1).strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("未找到 JSON 对象")
    blob = raw[start : end + 1]
    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        # 偶发单引号 / True/False 类 Python 字面量
        data = ast.literal_eval(blob)
    if not isinstance(data, dict):
        raise ValueError(f"JSON 根须为 object，实际 {type(data).__name__}")
    return data


async def _generate_flow_ir_via_json_text(
    model: Any,
    *,
    messages: list[dict[str, str]],
    label: str,
) -> FlowIr:
    """
    无 structured / tool_choice 时的兜底：普通 chat + JSON 解析。

    适用于 DeepSeek thinking 等既不支持 response_format 也不支持 tool_choice 的模型。
    """
    import asyncio

    from app.config import settings

    timeout = settings.agent_llm_plan_timeout_seconds
    # 强调只输出 JSON，避免 thinking 长文淹没
    prompt_messages = [
        *messages[:-1],
        {
            "role": "user",
            "content": str(messages[-1].get("content") or "")
            + "\n\n请只输出一个 JSON 对象，不要 markdown 说明。",
        },
    ]
    try:
        ai_msg = await asyncio.wait_for(model.ainvoke(prompt_messages), timeout=timeout)
    except TimeoutError as exc:
        raise TimeoutError(f"{label} 超时") from exc
    content = getattr(ai_msg, "content", ai_msg)
    if isinstance(content, list):
        # 多模态 / content blocks → 拼接文本
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text") or ""))
            else:
                text_attr = getattr(block, "text", None)
                if text_attr:
                    parts.append(str(text_attr))
        content = "\n".join(parts)
    if not isinstance(content, str):
        content = str(content)
    try:
        data = _extract_json_object(content)
    except Exception:
        logger.warning(
            "%s JSON 解析失败，原文预览: %s",
            label,
            (content or "")[:400].replace("\n", " "),
        )
        raise
    return FlowIr.model_validate(data)


async def generate_flow_ir(
    message: str,
    *,
    model_id: str,
) -> FlowIr | None:
    """调用 LLM 生成 FlowIr；失败返回 None。"""
    if not is_llm_flow_compile_enabled():
        return None

    msg = (message or "").strip()
    if not msg:
        return None

    try:
        from app.models.router import resolve_chat_model
        from app.services.llm_structured_invoke import ainvoke_structured_with_timeout

        # 门控内 IR：独立非流式模型，避免 astream_events 自动升级流式泄漏到 SSE
        model = resolve_chat_model(model_id, streaming=False).with_config(
            {"tags": ["nostream", "flow_ir_internal"]}
        )
        # Runnable 静态类型未暴露 with_structured_output；运行时 chat model 具备该方法
        structured_model: Any = model
        # 部分模型（如 deepseek）不支持原生 response_format / json_schema；
        # 官方备选 method=function_calling（tool calling 策略）。
        try:
            structured = structured_model.with_structured_output(FlowIr)
        except Exception:
            structured = structured_model.with_structured_output(FlowIr, method="function_calling")
        structured = structured.with_config({"tags": ["nostream", "flow_ir_internal"]})
        system = (
            _load_prompt()
            .replace("{{TOOL_LIST}}", _tool_list_for_prompt())
            .replace("{{FIELD_WHITELIST}}", _field_whitelist_for_prompt())
        )
        user_content = (
            f"使用者需求：{msg}\n\n"
            "若非条件分支任务，返回空 conditions 与空 nodes（服务端将回退）。"
            "否则输出完整 FlowIr JSON。"
        )

        from platform_mcp.runtime.agent_debug import agent_debug, preview_text

        agent_debug(
            "flow.ai.flow_ir.request",
            model_id=model_id,
            user_prompt=preview_text(user_content, max_len=400),
        )

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ]
        try:
            result: FlowIr = await ainvoke_structured_with_timeout(
                structured,
                messages,
                label="LLM Flow IR 生成",
            )
        except Exception as first_exc:
            logger.warning(
                "LLM Flow IR 原生 structured 失败，尝试 function_calling: %s",
                first_exc,
            )
            try:
                structured_fc = structured_model.with_structured_output(
                    FlowIr, method="function_calling"
                )
                result = await ainvoke_structured_with_timeout(
                    structured_fc,
                    messages,
                    label="LLM Flow IR 生成(function_calling)",
                )
            except Exception as second_exc:
                # DeepSeek thinking 等：tool_choice / json_schema 均不可用 → 纯文本 JSON
                logger.warning(
                    "LLM Flow IR function_calling 失败，改用 JSON 文本解析: %s",
                    second_exc,
                )
                result = await _generate_flow_ir_via_json_text(
                    model,
                    messages=messages,
                    label="LLM Flow IR 生成(json_text)",
                )
        if not result.nodes or not result.conditions:
            logger.info("LLM Flow IR 判定为非条件任务，回退 D1")
            return None
        return normalize_and_validate_flow_ir(result)
    except Exception as exc:
        logger.warning("LLM Flow IR 生成失败，回退 D1: %s", exc)
        return None


async def try_compile_conditional_plan(
    message: str,
    *,
    model_id: str,
    metadata: dict[str, Any] | None = None,
) -> CompiledConditionalPlan | None:
    """
    门控一站式：LLM IR（自行判断是否条件任务）→ 编译 → validate。

    不再用正则「猜」条件意图；非条件时模型返回空 conditions，此处回退 None。
    """
    from app.services.bpmn_observability import CompileTimer, record_bpmn_compile

    _ = metadata
    timer = CompileTimer()
    if not is_llm_flow_compile_enabled():
        record_bpmn_compile(
            ok=False,
            fallback="disabled",
            reason="feature_flag_off",
            duration_ms=timer.elapsed_ms(),
        )
        return None

    ir = await generate_flow_ir(message, model_id=model_id)
    if ir is None:
        record_bpmn_compile(
            ok=False,
            fallback="d1",
            reason="ir_none_or_non_conditional",
            duration_ms=timer.elapsed_ms(),
        )
        return None

    try:
        doc = compile_flow_document(ir)
        from app.services.bpmn_orchestration import (
            flow_document_to_plan_steps,
            validate_flow_document,
        )
        from app.services.flow_ir import flow_ir_to_params_by_tool

        validation = validate_flow_document(doc)
        if not validation.get("valid"):
            logger.warning(
                "编译后 FlowDocument 校验失败，回退 D1: %s",
                validation.get("errors"),
            )
            record_bpmn_compile(
                ok=False,
                fallback="d1",
                reason="validate_failed",
                duration_ms=timer.elapsed_ms(),
                condition_count=len(ir.conditions),
            )
            return None

        try:
            steps = flow_document_to_plan_steps(doc)
        except ValueError:
            steps = flow_ir_to_plan_steps(ir)
        if len(steps) < 2:
            record_bpmn_compile(
                ok=False,
                fallback="d1",
                reason="steps_lt_2",
                duration_ms=timer.elapsed_ms(),
                condition_count=len(ir.conditions),
            )
            return None

        for step in steps:
            if step.get("status") != "skipped":
                step["status"] = "awaiting_confirm"

        params_by_tool = flow_ir_to_params_by_tool(ir)
        logger.info(
            "条件 FlowDocument 编译成功: tools=%s params_tools=%s",
            [s.get("tool") for s in steps],
            list(params_by_tool.keys()),
        )
        record_bpmn_compile(
            ok=True,
            fallback="none",
            reason="compiled",
            duration_ms=timer.elapsed_ms(),
            condition_count=len(ir.conditions),
        )
        return CompiledConditionalPlan(
            flow_document=doc,
            steps=steps,
            ir=ir,
            params_by_tool=params_by_tool,
        )
    except Exception as exc:
        logger.warning("条件 FlowDocument 编译失败，回退 D1: %s", exc)
        record_bpmn_compile(
            ok=False,
            fallback="d1",
            reason=f"compile_exception:{type(exc).__name__}",
            duration_ms=timer.elapsed_ms(),
        )
        return None


def compile_flow_document_from_dict(raw: dict[str, Any]) -> dict[str, Any]:
    """测试 / 手工构造：dict → FlowIr → FlowDocument。"""
    ir = FlowIr.model_validate(raw)
    return compile_flow_document(ir)


# 供单测直接构造 IR
__all__ = [
    "CompiledConditionalPlan",
    "compile_flow_document",
    "compile_flow_document_from_dict",
    "flow_ir_to_plan_steps",
    "generate_flow_ir",
    "is_llm_flow_compile_enabled",
    "looks_like_conditional_intent",
    "try_compile_conditional_plan",
    "FlowIr",
    "FlowIrCondition",
    "FlowIrTaskNode",
]
