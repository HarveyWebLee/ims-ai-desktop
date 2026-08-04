"""工具生命周期 Hooks 领域模型（P2-1）。

对齐 Cursor Lifecycle Hooks 思路：before/after 可审计、可拦截。
不替代 LangGraph interrupt / HITL；拒绝时返回统一 ToolResult JSON。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from app.domain.tool_execution import ToolExecutionContext

ToolHookAction = Literal["allow", "deny"]


@dataclass(frozen=True)
class ToolHookDecision:
    """before_tool 决策：allow 继续；deny 短路并返回 ToolResult。"""

    action: ToolHookAction
    reason: str = ""
    code: str = "tool_hook_denied"

    @classmethod
    def allow(cls) -> ToolHookDecision:
        return cls(action="allow")

    @classmethod
    def deny(
        cls,
        reason: str,
        *,
        code: str = "tool_hook_denied",
    ) -> ToolHookDecision:
        return cls(action="deny", reason=reason, code=code)

    @property
    def allowed(self) -> bool:
        return self.action == "allow"


class ToolLifecycleHook(Protocol):
    """工具前后钩子端口；复合注册表按序调用。"""

    name: str

    def before_tool(
        self,
        tool_name: str,
        args: dict,
        context: ToolExecutionContext,
    ) -> ToolHookDecision:
        """真实 MCP/本地调用前；deny 则不再调用工具。"""
        ...

    def after_tool(
        self,
        tool_name: str,
        args: dict,
        result: str,
        context: ToolExecutionContext,
    ) -> None:
        """工具返回后（含 HITL 还原后的最终文本）；仅观测，不改结果。"""
        ...
