"""运行时工具 Hooks：注册表、默认策略、Pipeline/ReAct 共用入口。"""

from __future__ import annotations

import logging
from typing import Any

from app.domain.tool_execution import ToolExecutionContext
from app.domain.tool_hooks import ToolHookDecision, ToolLifecycleHook
from contracts.result import tool_result

logger = logging.getLogger(__name__)


class DenyListToolHook:
    """按配置拒绝指定工具名（逗号分隔名单）。"""

    name = "deny_list"

    def __init__(self, deny_tools: frozenset[str]) -> None:
        self._deny = deny_tools

    def before_tool(
        self,
        tool_name: str,
        args: dict,
        context: ToolExecutionContext,
    ) -> ToolHookDecision:
        _ = args, context
        if tool_name in self._deny:
            return ToolHookDecision.deny(
                f"工具「{tool_name}」已被运行时 Hooks 拒绝（deny_list）",
                code="tool_hook_deny_list",
            )
        return ToolHookDecision.allow()

    def after_tool(
        self,
        tool_name: str,
        args: dict,
        result: str,
        context: ToolExecutionContext,
    ) -> None:
        _ = tool_name, args, result, context


class AuditToolHook:
    """
    审计钩子：拒绝写入 tool_hook_deny；after 写入 tool_hook_after（可选）。

    默认 after 开启，便于运营确认 Hooks 链路；payload 已脱敏截断。
    """

    name = "audit"

    def __init__(self, *, audit_after: bool = True) -> None:
        self._audit_after = audit_after

    def before_tool(
        self,
        tool_name: str,
        args: dict,
        context: ToolExecutionContext,
    ) -> ToolHookDecision:
        _ = tool_name, args, context
        return ToolHookDecision.allow()

    def after_tool(
        self,
        tool_name: str,
        args: dict,
        result: str,
        context: ToolExecutionContext,
    ) -> None:
        if not self._audit_after:
            return
        _append_hook_audit(
            event_type="tool_hook_after",
            tool_name=tool_name,
            context=context,
            summary={
                "tool": tool_name,
                "args": args,
                "result_preview": (result or "")[:200],
                "hook": self.name,
            },
        )


class CompositeToolHook:
    """按序执行多个钩子；任一 before deny 即短路。"""

    name = "composite"

    def __init__(self, hooks: list[ToolLifecycleHook]) -> None:
        self._hooks = list(hooks)

    def before_tool(
        self,
        tool_name: str,
        args: dict,
        context: ToolExecutionContext,
    ) -> ToolHookDecision:
        for hook in self._hooks:
            decision = hook.before_tool(tool_name, args, context)
            if not decision.allowed:
                _append_hook_audit(
                    event_type="tool_hook_deny",
                    tool_name=tool_name,
                    context=context,
                    summary={
                        "tool": tool_name,
                        "args": args,
                        "hook": getattr(hook, "name", hook.__class__.__name__),
                        "code": decision.code,
                        "reason": decision.reason,
                    },
                )
                return decision
        return ToolHookDecision.allow()

    def after_tool(
        self,
        tool_name: str,
        args: dict,
        result: str,
        context: ToolExecutionContext,
    ) -> None:
        for hook in self._hooks:
            try:
                hook.after_tool(tool_name, args, result, context)
            except Exception:  # noqa: BLE001
                logger.debug(
                    "tool hook after failed: hook=%s tool=%s",
                    getattr(hook, "name", "?"),
                    tool_name,
                    exc_info=True,
                )


_hooks: ToolLifecycleHook | None = None


def _parse_deny_set(raw: str) -> frozenset[str]:
    return frozenset(x.strip() for x in (raw or "").split(",") if x.strip())


def build_default_tool_hooks() -> ToolLifecycleHook:
    """按当前 settings 组装默认复合钩子。"""
    from app.config import settings

    hooks: list[ToolLifecycleHook] = []
    deny = _parse_deny_set(settings.agent_tool_hook_deny_tools)
    if deny:
        hooks.append(DenyListToolHook(deny))
    if settings.agent_tool_hooks_audit_after:
        hooks.append(AuditToolHook(audit_after=True))
    return CompositeToolHook(hooks)


def get_tool_hooks() -> ToolLifecycleHook:
    """获取当前 Hooks（懒加载默认实现）。"""
    global _hooks
    if _hooks is None:
        _hooks = build_default_tool_hooks()
    return _hooks


def configure_tool_hooks(hooks: ToolLifecycleHook | None) -> ToolLifecycleHook | None:
    """替换 Hooks；传 None 下次 get 时按 settings 重建。返回旧实例。"""
    global _hooks
    previous = _hooks
    _hooks = hooks
    return previous


def reset_tool_hooks() -> None:
    """测试用：清空缓存，下次按 settings 重建。"""
    configure_tool_hooks(None)


def hooks_enabled() -> bool:
    from app.config import settings

    return bool(settings.agent_tool_hooks_enabled)


def denied_hook_result(tool_name: str, decision: ToolHookDecision) -> str:
    """Hooks 拒绝 → 统一 ToolResult（不可重试）。"""
    return tool_result(
        ok=False,
        summary=decision.reason or "运行时 Hooks 拒绝该工具",
        data={
            "error_code": decision.code or "tool_hook_denied",
            "tool": tool_name,
            "non_retryable": True,
        },
    )


def _resolve_hook_context(
    context: ToolExecutionContext | None,
) -> ToolExecutionContext:
    """补齐 thread/user，避免与 tool_execution 循环 import。"""
    from app.middleware.auth import resolve_user_id_from_token
    from contracts.context import current_auth_token, current_thread_id

    base = context or ToolExecutionContext()
    auth = base.auth_token if base.auth_token is not None else current_auth_token.get()
    tid = base.thread_id or current_thread_id.get()
    principal = base.principal_id or resolve_user_id_from_token(auth)
    return ToolExecutionContext(
        auth_token=auth,
        thread_id=tid,
        principal_id=principal,
        attributes=dict(base.attributes),
    )


def run_before_tool_hooks(
    tool_name: str,
    args: dict[str, Any],
    *,
    context: ToolExecutionContext | None = None,
) -> str | None:
    """
    调用前钩子。返回 None=放行；返回 str=已构造的拒绝 ToolResult JSON。
    关闭 Hooks 时恒放行。
    """
    if not hooks_enabled():
        return None
    ctx = _resolve_hook_context(context)
    decision = get_tool_hooks().before_tool(tool_name, dict(args), ctx)
    if decision.allowed:
        return None
    return denied_hook_result(tool_name, decision)


def run_after_tool_hooks(
    tool_name: str,
    args: dict[str, Any],
    result: str,
    *,
    context: ToolExecutionContext | None = None,
) -> None:
    """调用后钩子（失败静默）。"""
    if not hooks_enabled():
        return
    ctx = _resolve_hook_context(context)
    try:
        get_tool_hooks().after_tool(tool_name, dict(args), result, ctx)
    except Exception:  # noqa: BLE001
        logger.debug("run_after_tool_hooks failed tool=%s", tool_name, exc_info=True)


def _append_hook_audit(
    *,
    event_type: str,
    tool_name: str,
    context: ToolExecutionContext,
    summary: dict[str, Any],
) -> None:
    try:
        from app.services.audit_store import audit_store, mask_payload_summary
        from contracts.context import current_thread_id

        tid = (context.thread_id or current_thread_id.get() or "").strip()
        if not tid:
            return
        audit_store.append(
            thread_id=tid,
            user_id=str(context.principal_id or "anonymous"),
            event_type=event_type,
            tool_name=tool_name,
            payload_summary=mask_payload_summary(summary),
        )
    except Exception:  # noqa: BLE001
        logger.debug("hook audit append failed", exc_info=True)
