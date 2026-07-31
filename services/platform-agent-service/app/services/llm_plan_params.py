"""
Plan 阶段 LLM 工具参数抽取。

文件职责
--------
在多步 Plan 已确定「有哪些工具步骤」后，再调一次 LLM，
从用户原话里抽出各工具参数（时间、状态、路径、设备槽位等）。
与规则层 ``infer_plan_params`` 互补：LLM 懂口语化时间；规则负责校验与回退。

在 Agent 流程中的位置
--------------------
    prepare_plan_confirm_gate_async
      → resolve_task_plan（得到 steps）
      → generate_llm_plan_params（本模块，可选）
      → merge_plan_params（规则 + LLM 合并）
      → plan_confirm interrupt 展示预填参数

白话解释
--------
用户说「查近一小时告警并导出」：
规则能猜出两个工具；LLM 再把「近一小时」填进 start_time。
LLM 失败或超时 → 只用规则参数，不挡门控。

如何被调用
----------
- ``plan_confirm.prepare_plan_confirm_gate_async``
- 开关：``settings.agent_llm_plan_enabled``（总开关）/
  ``agent_llm_plan_params_enabled``（调用方另判）
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from platform_mcp.runtime.time_range import format_reference_hint, resolve_alarm_time_range
from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

# LLM 可填字段白名单（按工具名）；白名单外字段一律丢弃，防 hallucination
_TOOL_PARAM_KEYS: dict[str, frozenset[str]] = {
    "query_alarms": frozenset({"start_time", "end_time", "status", "alarm_level"}),
    "download_file": frozenset(
        {
            "resource",
            "start_time",
            "end_time",
            "status",
            "alarm_level",
            "sentry_id",
            "person_id",
        }
    ),
    "navigate_to": frozenset({"path"}),
    "get_alarm_detail": frozenset({"alarm_id"}),
    "open_alarm_detail": frozenset({"alarm_id"}),
    "query_devices": frozenset({"search", "device_name", "device_code", "online_status"}),
    "get_device_detail": frozenset({"device_code", "device_name"}),
    "query_device_variables": frozenset({"device_code", "device_name", "var_name"}),
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
    "open_device_detail": frozenset({"device_code", "device_name"}),
}


class LlmToolParamsEntry(BaseModel):
    """
    单工具参数字段（structured output 一行）。

    未在用户原话提及的字段请模型填空字符串，清洗阶段会丢掉空串。
    """

    tool: str = Field(description="工具名，须与 steps 一致")
    start_time: str = Field(default="", description="起始时间或相对原话")
    end_time: str = Field(default="", description="结束时间，相对范围通常留空")
    status: str = Field(default="", description="告警状态筛选")
    alarm_level: str = Field(default="", description="告警级别")
    resource: str = Field(default="", description="download_file 资源类型")
    sentry_id: str = Field(default="", description="岗哨交接导出可选岗哨 ID")
    path: str = Field(default="", description="navigate_to 目标")
    alarm_id: str = Field(default="", description="告警编号")
    search: str = Field(default="", description="设备模糊搜索")
    device_code: str = Field(default="", description="设备编码")
    device_name: str = Field(default="", description="设备名称")
    online_status: str = Field(default="", description="设备在线状态")
    var_name: str = Field(default="", description="设备变量名")
    variable_name: str = Field(default="", description="下发指令变量名")
    variable_value: str = Field(default="", description="下发指令写入值")
    operate_name: str = Field(default="", description="操作说明")


class LlmPlanParamsOut(BaseModel):
    """LLM 结构化参数响应：多工具 params 列表。"""

    params: list[LlmToolParamsEntry] = Field(default_factory=list, max_length=8)


def _load_prompt() -> str:
    """读取 llm_plan_params.md 系统提示词模板。"""
    return (_PROMPTS_DIR / "llm_plan_params.md").read_text(encoding="utf-8")


def _step_list_for_prompt(steps: list[dict[str, Any]]) -> str:
    """把 Plan 步骤格式化为注入 prompt 的 Markdown 列表。"""
    lines: list[str] = []
    for step in steps:
        tool = str(step.get("tool") or "")
        if not tool:
            continue
        label = str(step.get("label") or tool)
        lines.append(f"- 步骤 {step.get('id', '?')}：`{tool}` — {label}")
    return "\n".join(lines) if lines else "- （无）"


def _has_text(value: Any) -> bool:
    """非空文本判断（合并参数时跳过空串）。"""
    return bool(str(value or "").strip())


def _time_params_resolvable(start_time: str, end_time: str) -> bool:
    """判断时间参数能否被服务端解析为有效区间（相对/绝对均可）。"""
    return (
        resolve_alarm_time_range(
            str(start_time or "").strip(),
            str(end_time or "").strip(),
        )
        is not None
    )


def sanitize_llm_tool_params(
    tool: str,
    raw: dict[str, Any],
) -> dict[str, Any]:
    """
    清洗 LLM 输出的单工具参数。

    规则
    ----
    - 仅保留白名单字段
    - 空字符串丢弃
    - download_file 缺 resource 时默认 alarm_report
    - 时间字段无法 resolve 时整对删除（避免脏参数进 HITL）
    """
    name = (tool or "").strip()
    allowed = _TOOL_PARAM_KEYS.get(name, frozenset())
    cleaned: dict[str, Any] = {}

    for key in allowed:
        if key not in raw:
            continue
        val = raw.get(key)
        if val is None:
            continue
        if isinstance(val, str):
            text = val.strip()
            if not text:
                continue
            cleaned[key] = text
        else:
            cleaned[key] = val

    if name == "download_file" and "resource" not in cleaned:
        cleaned["resource"] = "alarm_report"

    start = str(cleaned.get("start_time") or "")
    end = str(cleaned.get("end_time") or "")
    if start or end:
        if not _time_params_resolvable(start, end):
            cleaned.pop("start_time", None)
            cleaned.pop("end_time", None)

    return cleaned


def merge_tool_params(
    base: dict[str, Any],
    overlay: dict[str, Any],
) -> dict[str, Any]:
    """
    合并规则参数与 LLM 参数：LLM 非空且合法字段覆盖 base。

    时间字段成对校验：只有连同 base 一起仍能 resolve，才写入 overlay 的时间，
    避免只覆盖 start_time 导致后续 resolve 失败。
    """
    result = dict(base)
    for key, value in overlay.items():
        if key in ("start_time", "end_time"):
            continue
        if not _has_text(value) and not isinstance(value, (list, dict)):
            continue
        result[key] = value

    # 时间单独试合并：trial 可解析才真正 update
    time_overlay: dict[str, Any] = {}
    for key in ("start_time", "end_time"):
        if key not in overlay:
            continue
        value = overlay.get(key)
        if _has_text(value):
            time_overlay[key] = value

    if time_overlay:
        trial = dict(result)
        trial.update(time_overlay)
        if _time_params_resolvable(
            str(trial.get("start_time") or ""),
            str(trial.get("end_time") or ""),
        ):
            result.update(time_overlay)
    return result


def normalize_llm_plan_params(
    raw_params: list[LlmToolParamsEntry],
    steps: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """
    将 LLM 列表转为 ``params_by_tool`` 字典。

    仅保留 steps 中出现的工具；同工具名只取首次，防止重复条目打架。
    """
    step_tools = {str(s.get("tool") or "") for s in steps if s.get("tool")}
    out: dict[str, dict[str, Any]] = {}
    for entry in raw_params:
        tool = (entry.tool or "").strip()
        if tool not in step_tools or tool in out:
            continue
        payload = entry.model_dump(exclude={"tool"}, exclude_none=False)
        sanitized = sanitize_llm_tool_params(tool, payload)
        # 部分工具即使清洗后为空 dict 也保留键，便于门控侧统一遍历
        if sanitized or tool in ("navigate_to", "get_alarm_detail", "open_alarm_detail"):
            out[tool] = sanitized
    return out


async def generate_llm_plan_params(
    message: str,
    steps: list[dict[str, Any]],
    *,
    model_id: str,
) -> dict[str, dict[str, Any]] | None:
    """
    调用 LLM 从用户原话抽取 Plan 各步工具参数。

    返回 None 的情况（由规则 ``infer_plan_params`` 兜底）
    -----------------------------------------------
    - ``agent_llm_plan_enabled`` 关闭
    - 空消息或步骤不足 2
    - 超时 / 结构化解析失败 / 其他异常

    返回
    ----
    dict[str, dict] | None
        工具名 → 参数字典；无有效内容时也返回 None。
    """
    if not settings.agent_llm_plan_enabled:
        return None

    msg = (message or "").strip()
    if not msg or len(steps) < 2:
        return None

    try:
        from app.models.router import resolve_chat_model
        from app.services.llm_structured_invoke import ainvoke_structured_with_timeout

        model = resolve_chat_model(model_id)
        structured = model.with_structured_output(LlmPlanParamsOut)

        system = (
            _load_prompt()
            .replace("{{CURRENT_TIME}}", format_reference_hint())
            .replace("{{STEP_LIST}}", _step_list_for_prompt(steps))
        )
        user_content = f"使用者原话：{msg}\n\n请为上述步骤中的每个工具输出 params JSON。"

        from platform_mcp.runtime.agent_debug import agent_debug, preview_text, summarize_plan_steps

        agent_debug(
            "flow.ai.llm_plan_params.request",
            model_id=model_id,
            user_prompt=preview_text(user_content, max_len=400),
            plan_steps=summarize_plan_steps(steps),
        )

        result: LlmPlanParamsOut = await ainvoke_structured_with_timeout(
            structured,
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            label="LLM Plan 参数抽取",
        )
        params = normalize_llm_plan_params(result.params, steps)
        agent_debug(
            "flow.ai.llm_plan_params.response",
            model_id=model_id,
            llm_plan_params=params,
        )
        if params:
            logger.info(
                "LLM Plan 参数抽取成功: tools=%s",
                list(params.keys()),
            )
        return params or None
    except Exception as exc:
        logger.warning("LLM Plan 参数抽取失败，回退规则: %s", exc)
        return None
