"""
LLM structured output 调用辅助：统一超时包装。

文件职责
--------
对 LangChain ``with_structured_output(...).ainvoke`` 套一层 ``asyncio.wait_for``，
避免在 plan_confirm 门控、参数抽取等「用户还在等第一帧 SSE」的路径上
因模型卡住导致前端长时间无事件。

在 Agent 流程中的位置
--------------------
    generate_llm_task_plan / generate_llm_plan_params
      → ainvoke_structured_with_timeout(structured, messages, label=...)
      → 成功：返回 Pydantic 结构化结果
      → 超时：抛 TimeoutError，上层记录 warning 并回退规则引擎

白话解释
--------
结构化输出 = 要求模型按固定 schema 吐 JSON。
若模型半天不回，不能无限挂着；超时后由调用方改用规则 Plan / 规则参数。

如何被调用
----------
- ``app.services.llm_task_planner``
- ``app.services.llm_plan_params``
- 默认超时秒数：``settings.agent_llm_plan_timeout_seconds``
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


async def ainvoke_structured_with_timeout(
    structured_model: Any,
    messages: list[dict[str, str]],
    *,
    label: str,
    timeout_seconds: float | None = None,
) -> Any:
    """
    带超时的 ``structured.ainvoke``。

    参数
    ----
    structured_model :
        已绑定 Pydantic schema 的 chat model（``model.with_structured_output(...)``）。
    messages :
        OpenAI 风格 ``[{role, content}, ...]``，通常含 system + user。
    label : str
        打日志用的中文标签，如「LLM Plan 生成」。
    timeout_seconds : float | None
        覆盖默认超时；None 则读配置 ``agent_llm_plan_timeout_seconds``。

    返回
    ----
    T
        结构化解析后的 Pydantic 模型实例。

    异常
    ----
    TimeoutError
        超时后抛出（由 asyncio.TimeoutError 转换），供上层捕获并回退规则。
    """
    timeout = (
        timeout_seconds if timeout_seconds is not None else settings.agent_llm_plan_timeout_seconds
    )
    try:
        return await asyncio.wait_for(
            structured_model.ainvoke(messages),
            timeout=timeout,
        )
    except TimeoutError as exc:
        logger.warning("%s 超时（%.0fs），回退规则", label, timeout)
        # 转为内置 TimeoutError，调用方可用 except Exception / TimeoutError 统一处理
        raise TimeoutError(f"{label} 超时") from exc
