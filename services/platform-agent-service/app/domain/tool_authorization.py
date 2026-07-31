"""基于 catalog 的工具授权策略。"""

from __future__ import annotations

from typing import Any

from app.domain.tool_execution import (
    ToolAuthorizationDecision,
    ToolExecutionRequest,
)


class CatalogRequiredPermissionsPolicy:
    """
    读取 catalog.required_permissions 并与上下文权限声明比对。

    策略（写工具 fail-closed，可由 ``AGENT_TOOL_PERMISSION_FAIL_CLOSED`` 回滚）：
    - 工具未声明 required_permissions → 放行
    - 已注入 permissions 时，必须覆盖全部 required_permissions
    - 上下文尚未注入 permissions：
      - fail_closed=true（默认）→ 拒绝（避免权限模型形同虚设）
      - fail_closed=false → 兼容放行（仅本地联调临时开关）
    """

    def authorize(self, request: ToolExecutionRequest) -> ToolAuthorizationDecision:
        from app.config import settings
        from contracts.tool_catalog_loader import get_tool_manifest

        manifest = get_tool_manifest(request.tool_name)
        required = _as_str_list((manifest or {}).get("required_permissions"))
        if not required:
            return ToolAuthorizationDecision.allow()

        granted_raw = request.context.attributes.get("permissions")
        if granted_raw is None:
            if settings.agent_tool_permission_fail_closed:
                return ToolAuthorizationDecision.deny(
                    "当前会话未声明工具权限，拒绝执行需授权的写操作",
                    code="tool_permission_context_missing",
                )
            return ToolAuthorizationDecision.allow()

        granted = set(_as_str_list(granted_raw))
        missing = [permission for permission in required if permission not in granted]
        if not missing:
            return ToolAuthorizationDecision.allow()

        return ToolAuthorizationDecision.deny(
            f"当前用户缺少工具权限：{', '.join(missing)}",
            code="tool_permission_denied",
        )


def _as_str_list(value: Any) -> list[str]:
    """将权限声明规范化为字符串列表。"""
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, (list, tuple, set, frozenset)):
        return [str(item).strip() for item in value if str(item).strip()]
    return []
