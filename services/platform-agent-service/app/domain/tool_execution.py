"""工具执行领域模型与授权策略协议。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class ToolExecutionContext:
    """工具调用所需的请求上下文，不依赖具体 Web 或 Agent 框架。"""

    auth_token: str | None = None
    thread_id: str | None = None
    principal_id: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolExecutionRequest:
    """一次工具执行请求，授权策略可基于工具名、参数与调用主体决策。"""

    tool_name: str
    args: dict[str, Any]
    context: ToolExecutionContext = field(default_factory=ToolExecutionContext)

    def with_args(self, args: dict[str, Any]) -> ToolExecutionRequest:
        """返回参数已归一化的新请求，保留原执行上下文。"""
        return ToolExecutionRequest(
            tool_name=self.tool_name,
            args=dict(args),
            context=self.context,
        )


@dataclass(frozen=True)
class ToolAuthorizationDecision:
    """工具授权决策。拒绝时 reason 用于生成可解释的 ToolResult。"""

    allowed: bool
    reason: str = ""
    code: str = ""

    @classmethod
    def allow(cls) -> ToolAuthorizationDecision:
        """创建放行决策。"""
        return cls(allowed=True)

    @classmethod
    def deny(
        cls,
        reason: str,
        *,
        code: str = "tool_permission_denied",
    ) -> ToolAuthorizationDecision:
        """创建拒绝决策。"""
        return cls(allowed=False, reason=reason, code=code)


class ToolAuthorizationPolicy(Protocol):
    """工具授权策略端口；未来 RBAC/ABAC/平台权限适配器均实现本协议。"""

    def authorize(self, request: ToolExecutionRequest) -> ToolAuthorizationDecision:
        """根据调用主体、工具和归一化参数返回授权决策。"""
        ...


class AllowAllToolAuthorizationPolicy:
    """兼容当前行为的默认策略：所有已注册工具均放行。"""

    def authorize(self, request: ToolExecutionRequest) -> ToolAuthorizationDecision:
        _ = request
        return ToolAuthorizationDecision.allow()
