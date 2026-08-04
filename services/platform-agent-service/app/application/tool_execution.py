"""统一工具执行管线：preflight → authorization → invoke。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langgraph.errors import GraphInterrupt

from app.domain.tool_authorization import CatalogRequiredPermissionsPolicy
from app.domain.tool_execution import (
    ToolAuthorizationDecision,
    ToolAuthorizationPolicy,
    ToolExecutionContext,
    ToolExecutionRequest,
)
from app.middleware.auth import (
    resolve_permissions_from_token,
    resolve_user_id_from_token,
)
from contracts.agent_debug import (
    agent_debug,
    summarize_tool_args,
    summarize_tool_result,
)
from contracts.context import (
    current_auth_token,
    current_hitl_confirm_bypass,
    current_thread_id,
    safe_reset_contextvar,
)
from contracts.result import tool_result


@dataclass(frozen=True)
class PreparedToolExecution:
    """preflight 与授权完成后的执行准备结果。"""

    request: ToolExecutionRequest
    interrupt: dict[str, Any] | None = None
    denied_result: str | None = None

    @property
    def ready(self) -> bool:
        """是否可进入真实工具调用。"""
        return self.interrupt is None and self.denied_result is None


@dataclass(frozen=True)
class ToolExecutionOutcome:
    """工具调用结果；HITL 中断与普通 ToolResult 互斥。"""

    result: str | None = None
    interrupt: dict[str, Any] | None = None


def enrich_tool_execution_context(
    context: ToolExecutionContext | None = None,
    *,
    auth_token: str | None = None,
    thread_id: str | None = None,
    principal_id: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> ToolExecutionContext:
    """补齐工具执行上下文中的身份与线程信息。"""
    base = context or ToolExecutionContext()
    resolved_auth = auth_token if auth_token is not None else base.auth_token
    if resolved_auth is None:
        resolved_auth = current_auth_token.get()
    resolved_thread = thread_id if thread_id is not None else base.thread_id
    if not resolved_thread:
        resolved_thread = current_thread_id.get()
    resolved_principal = principal_id if principal_id is not None else base.principal_id
    if not resolved_principal:
        resolved_principal = resolve_user_id_from_token(resolved_auth)
    merged_attributes = dict(base.attributes)
    # 仅当 JWT 声明了权限时注入；无声明则不写入，由 CatalogRequiredPermissionsPolicy fail-closed。
    if "permissions" not in merged_attributes:
        token_permissions = resolve_permissions_from_token(resolved_auth)
        if token_permissions is not None:
            merged_attributes["permissions"] = token_permissions
    if attributes:
        merged_attributes.update(attributes)
    return ToolExecutionContext(
        auth_token=resolved_auth,
        thread_id=resolved_thread,
        principal_id=resolved_principal,
        attributes=merged_attributes,
    )


def authorize_tool_call(
    tool_name: str,
    args: dict[str, Any] | None = None,
    *,
    context: ToolExecutionContext | None = None,
) -> ToolAuthorizationDecision:
    """对单次工具调用执行当前授权策略。"""
    request = ToolExecutionRequest(
        tool_name=tool_name,
        args=dict(args or {}),
        context=enrich_tool_execution_context(context),
    )
    return get_tool_authorization_policy().authorize(request)


def denied_tool_result(tool_name: str, decision: ToolAuthorizationDecision) -> str:
    """将授权拒绝转换为统一 ToolResult JSON（标记不可重试）。"""
    return tool_result(
        ok=False,
        summary=decision.reason or "当前用户无权执行该操作",
        data={
            "error_code": decision.code or "tool_permission_denied",
            "tool": tool_name,
            "non_retryable": True,
        },
    )


class ToolExecutionPipeline:
    """工具执行应用服务，集中承载参数、授权与调用上下文。"""

    def __init__(self, authorization_policy: ToolAuthorizationPolicy) -> None:
        self._authorization_policy = authorization_policy

    async def prepare(self, request: ToolExecutionRequest) -> PreparedToolExecution:
        """归一化参数并执行授权；不会调用实际工具。"""
        from contracts.tool_preflight import preflight_tool

        enriched = ToolExecutionRequest(
            tool_name=request.tool_name,
            args=dict(request.args),
            context=enrich_tool_execution_context(request.context),
        )
        # preflight（如 send_device_cmd resolver）会调平台 API，须带上 JWT ContextVar
        auth_reset = None
        tid_reset = None
        if enriched.context.auth_token is not None:
            auth_reset = current_auth_token.set(enriched.context.auth_token)
        if enriched.context.thread_id:
            tid_reset = current_thread_id.set(enriched.context.thread_id)
        try:
            preflight = preflight_tool(enriched.tool_name, enriched.args)
        finally:
            if tid_reset is not None:
                safe_reset_contextvar(
                    current_thread_id,
                    tid_reset,
                    label="current_thread_id",
                )
            if auth_reset is not None:
                safe_reset_contextvar(
                    current_auth_token,
                    auth_reset,
                    label="current_auth_token",
                )
        agent_debug(
            "flow.tool.preflight",
            tool=enriched.tool_name,
            args_in=summarize_tool_args(enriched.args),
            needs_interrupt=preflight.interrupt is not None,
            interrupt_type=(
                (preflight.interrupt or {}).get("type") if preflight.interrupt else None
            ),
            preflight_args=summarize_tool_args(preflight.args),
            has_auth=bool(enriched.context.auth_token),
        )
        normalized_request = enriched.with_args(preflight.args)
        if preflight.interrupt:
            return PreparedToolExecution(
                request=normalized_request,
                interrupt=preflight.interrupt,
            )

        from contracts.context import current_run_mode
        from contracts.tool_catalog_loader import is_write_tool

        if current_run_mode.get() == "readonly" and is_write_tool(enriched.tool_name):
            from app.services.tool_subset import deny_readonly_write_summary

            return PreparedToolExecution(
                request=normalized_request,
                denied_result=tool_result(
                    ok=False,
                    summary=deny_readonly_write_summary(enriched.tool_name),
                    data={
                        "error_code": "run_mode_readonly",
                        "tool": enriched.tool_name,
                        "non_retryable": True,
                    },
                ),
            )

        decision = self._authorization_policy.authorize(normalized_request)
        agent_debug(
            "flow.tool.authorization",
            tool=enriched.tool_name,
            allowed=decision.allowed,
            code=decision.code,
            has_principal=bool(normalized_request.context.principal_id),
        )
        if decision.allowed:
            # 授权通过后再跑 Hooks（不替代 interrupt / preflight）
            from app.services.tool_hooks import run_before_tool_hooks

            hook_denied = run_before_tool_hooks(
                enriched.tool_name,
                normalized_request.args,
                context=normalized_request.context,
            )
            if hook_denied is not None:
                return PreparedToolExecution(
                    request=normalized_request,
                    denied_result=hook_denied,
                )
            return PreparedToolExecution(request=normalized_request)

        return PreparedToolExecution(
            request=normalized_request,
            denied_result=denied_tool_result(enriched.tool_name, decision),
        )

    async def invoke(
        self,
        prepared: PreparedToolExecution,
        *,
        hitl_confirm_bypass: bool = False,
    ) -> ToolExecutionOutcome:
        """恢复请求上下文并以 ainvoke 调用已准备好的工具（MCP 多为 async-only）。"""
        if not prepared.ready:
            raise ValueError("工具尚未通过 preflight 与授权，不可执行")

        request = prepared.request
        captured_auth = (
            request.context.auth_token
            if request.context.auth_token is not None
            else current_auth_token.get()
        )
        captured_tid = request.context.thread_id or current_thread_id.get()
        captured_hitl_bypass = hitl_confirm_bypass or current_hitl_confirm_bypass.get()
        agent_debug(
            "flow.tool.invoke_context",
            tool=request.tool_name,
            has_auth=bool(captured_auth),
            has_thread_id=bool(captured_tid),
            auth_source="request" if request.context.auth_token is not None else "contextvar",
            hitl_confirm_bypass=captured_hitl_bypass,
        )

        from app.services.agent_tool_retry import invoke_tool_async

        auth_reset = current_auth_token.set(captured_auth)
        tid_reset = current_thread_id.set(captured_tid)
        bypass_reset = current_hitl_confirm_bypass.set(captured_hitl_bypass)
        try:
            result = await invoke_tool_async(request.tool_name, request.args)
        except GraphInterrupt:
            # 图内 interrupt：向上冒泡由父图 / astream 处理
            raise
        finally:
            safe_reset_contextvar(
                current_hitl_confirm_bypass,
                bypass_reset,
                label="current_hitl_confirm_bypass",
            )
            safe_reset_contextvar(current_thread_id, tid_reset, label="current_thread_id")
            safe_reset_contextvar(current_auth_token, auth_reset, label="current_auth_token")

        agent_debug(
            "flow.tool.invoke_done",
            tool=request.tool_name,
            result_summary=summarize_tool_result(result),
        )
        from app.services.tool_hooks import run_after_tool_hooks

        run_after_tool_hooks(
            request.tool_name,
            request.args,
            result if isinstance(result, str) else str(result or ""),
            context=request.context,
        )
        return ToolExecutionOutcome(result=result)


_authorization_policy: ToolAuthorizationPolicy = CatalogRequiredPermissionsPolicy()
_pipeline = ToolExecutionPipeline(_authorization_policy)


def get_tool_authorization_policy() -> ToolAuthorizationPolicy:
    """获取当前工具授权策略。"""
    return _authorization_policy


def get_tool_execution_pipeline() -> ToolExecutionPipeline:
    """获取当前工具执行管线。"""
    return _pipeline


def configure_tool_authorization_policy(
    policy: ToolAuthorizationPolicy,
) -> ToolAuthorizationPolicy:
    """
    替换工具授权策略并返回旧策略，便于启动注入与测试恢复。
    """
    global _authorization_policy, _pipeline
    previous = _authorization_policy
    _authorization_policy = policy
    _pipeline = ToolExecutionPipeline(policy)
    return previous
