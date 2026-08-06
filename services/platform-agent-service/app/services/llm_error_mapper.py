"""
LLM 调用异常 → 面向使用者的 SSE error 载荷。

文件职责
--------
把 OpenAI 兼容 API / LangChain 抛出的原始异常（含 HTTP 码、厂商 error dict）
映射为稳定的 ``kind + message + hint + detail``，避免前端直接展示 ``str(exc)``
技术堆栈。值班员看到的是可操作提示（换模型、检查 Key、开通按量付费等）。

在 Agent 流程中的位置
--------------------
    builder / chat 流式调用 LLM 失败
      → format_llm_error_event(exc)
      → SSE ``event: error`` 的 data 字段
    分类逻辑：classify_llm_exception（配额 / 鉴权 / 限流 / 网络…）

白话解释
--------
厂商报错像「Error code: 403 - {...}」，用户看不懂；
本模块翻译成：「免费额度用尽」+「去控制台开按量付费或换模型」。

如何被调用
----------
- 图执行 / SSE 包装层捕获 LLM 异常后调用
- ``code`` 默认 50002（与前端 Agent 错误码约定对齐）
"""

from __future__ import annotations

import ast
import json
import re
from typing import Any

# OpenAI / LangChain 常见包装：Error code: 403 - {...}
_OPENAI_ERROR_RE = re.compile(
    r"Error code:\s*(\d+)\s*-\s*(.+)",
    re.DOTALL,
)

# kind → 用户可见主文案（前端也可再按 kind 做 i18n）
_USER_MESSAGES: dict[str, str] = {
    "quota_exhausted": "当前模型免费额度已用尽或账户未开通按量付费",
    "auth": "模型 API Key 无效、过期或未配置",
    "rate_limit": "模型请求过于频繁，请稍后再试",
    "model_unavailable": "模型服务暂不可用，请稍后重试或切换其他模型",
    "network": "无法连接模型服务，请检查网络或代理配置",
    "mcp_unavailable": "平台工具服务（MCP）不可用，请确认已启动后再试",
    "unknown": "模型服务调用失败，请稍后重试",
}

# kind → 可操作补充说明
_HINTS: dict[str, str] = {
    "quota_exhausted": (
        "若使用通义（DashScope）：请前往阿里云百炼控制台开通按量付费，"
        "或在控制台关闭「仅使用免费额度」模式；也可在侧栏切换 DeepSeek 等其他模型。"
    ),
    "auth": "请检查 platform-agent-service/.env 中对应厂商的 API Key 是否正确。",
    "rate_limit": "请等待 1～2 分钟后重试，或切换到负载更低的模型。",
    "model_unavailable": "可在侧栏尝试切换 qwen3-32b 等默认模型。",
    "network": "请确认本机可访问模型 API 地址，且未错误配置代理。",
    "mcp_unavailable": (
        "请先启动 platform-mcp-server（默认 http://127.0.0.1:8010），"
        "或检查 PLATFORM_MCP_URL 配置后重试。"
    ),
}


def _truncate(text: str, limit: int = 400) -> str:
    """截断 detail，避免 SSE 载荷过大；末尾加省略号。"""
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _parse_error_payload(tail: str) -> dict[str, Any] | None:
    """
    尝试从异常尾部解析 JSON 或 Python dict 字面量。

    有的 SDK 把 body 打成 JSON；有的打成 ``{'error': ...}``（单引号），
    故依次尝试 ``json.loads`` 与 ``ast.literal_eval``。
    """
    raw = tail.strip()
    if not raw:
        return None
    for loader in (json.loads, ast.literal_eval):
        try:
            parsed = loader(raw)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError, SyntaxError, ValueError, TypeError:
            continue
    return None


def _nested_error_message(body: dict[str, Any]) -> str:
    """从厂商 body 取出 error.message 或顶层 message。"""
    err = body.get("error")
    if isinstance(err, dict):
        msg = err.get("message")
        if isinstance(msg, str) and msg.strip():
            return msg.strip()
    msg = body.get("message")
    return msg.strip() if isinstance(msg, str) else ""


def _nested_error_type(body: dict[str, Any]) -> str:
    """从厂商 body 取出 error.type / error.code / 顶层 code。"""
    err = body.get("error")
    if isinstance(err, dict):
        typ = err.get("type") or err.get("code")
        if isinstance(typ, str):
            return typ
    code = body.get("code")
    return code if isinstance(code, str) else ""


def classify_llm_exception(exc: BaseException) -> tuple[str, int | None, str | None]:
    """
    将任意 LLM 相关异常分类为稳定 kind。

    返回
    ----
    (kind, http_status, provider_error_type)
        kind 取值见 ``_USER_MESSAGES`` 的键；
        http_status 能从 ``Error code: N`` 解析时填入，否则 None；
        provider_error_type 为厂商 type/code 小写串，便于日志排查。

    分类优先级（简化）
    ------------------
    配额用尽 → 鉴权失败 → 限流 → 计费类 403/402 → 网关不可用 → 网络 → unknown
    """
    text = str(exc)
    lower = text.lower()
    http_status: int | None = None
    err_type = ""
    err_message = lower

    # 解析「Error code: 403 - {json}」形态，尽量拿到嵌套 message/type
    match = _OPENAI_ERROR_RE.search(text)
    if match:
        http_status = int(match.group(1))
        body = _parse_error_payload(match.group(2))
        if body:
            nested = _nested_error_message(body)
            if nested:
                err_message = nested.lower()
            err_type = _nested_error_type(body).lower()

    # 免费额度 / 配额（DashScope FreeTierOnly、OpenAI insufficient_quota 等）
    if (
        "allocationquota.freetieronly" in err_type
        or "free quota" in err_message
        or "free tier" in err_message
        or "quota has been exhausted" in err_message
        or "insufficient_quota" in err_type
        or "insufficient_quota" in err_message
        or "exceeded your current quota" in err_message
    ):
        return "quota_exhausted", http_status, err_type or None

    if http_status == 401 or "invalid_api_key" in err_type or "authentication" in err_message:
        return "auth", http_status, err_type or None

    if http_status == 429 or "rate limit" in err_message or "rate_limit" in err_type:
        return "rate_limit", http_status, err_type or None

    # 部分厂商用 403/402 表达未开通计费，而非鉴权失败
    if http_status in (403, 402) and ("quota" in err_message or "billing" in err_message):
        return "quota_exhausted", http_status, err_type or None

    if http_status in (502, 503, 504) or "overloaded" in err_message:
        return "model_unavailable", http_status, err_type or None

    if "connection" in lower or "timeout" in lower or "connect" in lower:
        return "network", http_status, err_type or None

    if (
        "platform mcp" in lower
        or "mcp 不可用" in text
        or "mcp不可用" in text
        or "platform-mcp-server" in lower
        or ("mcp" in lower and ("8010" in lower or "不可用" in text or "unavailable" in lower))
    ):
        return "mcp_unavailable", http_status, err_type or None

    return "unknown", http_status, err_type or None


def format_llm_error_event(
    exc: BaseException,
    *,
    code: int = 50002,
    fallback_message: str | None = None,
) -> dict[str, Any]:
    """
    构造 SSE ``error`` 事件 payload（对齐 ``{code, message, data}`` 语义）。

    参数
    ----
    exc : BaseException
        捕获到的原始异常。
    code : int
        业务错误码，默认 50002。
    fallback_message : str | None
        仅当 kind=unknown 时可用的自定义主文案（否则用内置 unknown）。

    返回
    ----
    dict
        ``message`` 面向用户；``data.kind`` 供前端分支展示；
        ``data.detail`` 为截断后的原始异常文本（排查用，勿直接整屏展示）。
    """
    kind, http_status, err_type = classify_llm_exception(exc)
    message = _USER_MESSAGES.get(kind, _USER_MESSAGES["unknown"])
    if fallback_message and kind == "unknown":
        message = fallback_message

    hint = _HINTS.get(kind)
    return {
        "code": code,
        "message": message,
        "data": {
            "kind": kind,
            "http_status": http_status,
            "error_type": err_type,
            "hint": hint,
            "detail": _truncate(str(exc)),
        },
    }


def format_error_assistant_content(payload: dict[str, Any] | None) -> str:
    """
    将 SSE error 载荷格式化为可写入 checkpoint / 历史气泡的助手正文。

    与桌面端 ``formatAgentErrorMessage`` + ``⚠️`` 前缀对齐，保证实时与历史观感一致。
    """
    if not isinstance(payload, dict):
        return f"⚠️ {_USER_MESSAGES['unknown']}"

    message = str(payload.get("message") or "").strip() or _USER_MESSAGES["unknown"]
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    hint = str((data or {}).get("hint") or "").strip()
    body = f"{message}\n\n{hint}" if hint else message
    return f"⚠️ {body}"
