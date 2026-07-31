"""
可选：从平台路由 TSX 提取可导航菜单路径，写入 navigation_routes.json。

默认以本仓已提交的 `app/data/navigation_routes.json` 为准。
若需重建，设置环境变量 PLATFORM_ROUTES_TSX 指向路由 TSX 后运行本脚本。
"""

from __future__ import annotations

import json
import os
import re  # 正则，从 TSX 块里提取 path、name 等字段
from datetime import UTC, datetime  # UTC 时区；datetime 生成 ISO 时间戳
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# 路径常量
# ---------------------------------------------------------------------------

SERVICE_ROOT = Path(__file__).resolve().parent.parent
# 可选：PLATFORM_ROUTES_TSX 指向平台 Web 路由 TSX；未设置则保留已有 navigation_routes.json
_routes_env = os.environ.get("PLATFORM_ROUTES_TSX", "").strip()
ROUTES_TSX = Path(_routes_env).expanduser() if _routes_env else None
OUT_JSON = SERVICE_ROOT / "app" / "data" / "navigation_routes.json"

# 写入 JSON 的「路由规范」说明，Agent Prompt 也会引用类似规则
ROUTE_RULES = """## 平台路由路径规范（navigate_to 必须遵守）

1. **只使用 originPath（浏览器地址栏路径）**，禁止使用组件 filePath。
2. **originPath 不含 groupId**：`meta.groupId` 仅用于前端组件懒加载目录，不出现在 URL 中。
   - 错误：`/config_management/config/monitor_equipment/equipment_manage`（含 groupId）
   - 正确：`/config_management/config/equipment_manage`
3. **拼接规则**（与 routes.tsx → processRoutes 一致）：
   - 顶层：`path` 以 `/` 开头时即为 originPath（如 `/overview`）
   - 子级：`父级 originPath + '/' + 当前 path`（如 `equipment_manage` → `/config_management/config/equipment_manage`）
4. **优先使用运行时注入的「常用页面路由」速查表**；不确定时传中文页面名，由工具解析别名。
5. **禁止**编造 `/device_management` 等未在速查表中的简写路径。"""


def _split_route_objects(routes_section: str) -> list[str]:
    """
    把 TSX 里 `_routes = [ { ... }, { ... } ]` 的数组内容，
    拆成多个顶层 `{...}` 字符串（每个对应一个路由对象）。

    难点：对象内部可能有嵌套 `{}`、字符串里的 `{`、引号转义等，
    所以用 depth 计数大括号，并跟踪是否在字符串内。

    参数:
        routes_section: `[` 和 `];` 之间的文本

    返回:
        例如 ['{ path: "/overview", ... }', '{ path: "config", children: [...] }']
    """
    objects: list[str] = []
    depth = 0  # 当前大括号嵌套深度
    start = -1  # 当前对象 `{` 的起始下标
    i = 0
    in_string = False  # 是否在 '...' 或 "..." 字符串内
    string_char = ""  # 当前字符串用的引号类型
    escape = False  # 上一字符是否是反斜杠转义

    while i < len(routes_section):
        ch = routes_section[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == string_char:
                in_string = False
            i += 1
            continue

        if ch in ("'", '"'):
            in_string = True
            string_char = ch
            i += 1
            continue

        if ch == "{":
            if depth == 0:
                start = i  # 记录顶层对象开始
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                # 切片 [start : i+1] 含头含尾，得到完整 {...}
                objects.append(routes_section[start : i + 1])
                start = -1
        i += 1

    return objects


def _parse_route_block(block: str) -> dict[str, Any] | None:
    """
    解析单个路由对象的 TSX 文本块，提取 path、name、isMenu、children 等。

    参数:
        block: 形如 `{ path: 'foo', name: '栏目标题', children: [ ... ] }` 的字符串

    返回:
        结构化 dict；若没有 path 则返回 None
    """
    path_m = re.search(r"\bpath:\s*['\"]([^'\"]+)['\"]", block)
    if not path_m:
        return None
    path = path_m.group(1)

    name_m = re.search(r"\bname:\s*['\"]([^'\"]+)['\"]", block)
    # 有 isMenu 关键字且不是 isMenu: false
    is_menu = bool(re.search(r"\bisMenu\b", block)) and not re.search(r"\bisMenu:\s*false\b", block)
    group_id_m = re.search(r"\bgroupId:\s*['\"]([^'\"]+)['\"]", block)
    group_m = re.search(r"\bgroup:\s*['\"]([^'\"]+)['\"]", block)
    children_m = re.search(r"\bchildren:\s*\[", block)

    children: list[dict[str, Any]] = []
    if children_m:
        inner = block[children_m.end() :]
        # 找到与 children: [ 匹配的 ]（同样要处理字符串和嵌套括号）
        depth = 1
        j = 0
        in_string = False
        string_char = ""
        escape = False
        while j < len(inner) and depth > 0:
            ch = inner[j]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == string_char:
                    in_string = False
                j += 1
                continue
            if ch in ("'", '"'):
                in_string = True
                string_char = ch
                j += 1
                continue
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    children_content = inner[:j]
                    for child_block in _split_route_objects(children_content):
                        child = _parse_route_block(child_block)
                        if child:
                            children.append(child)
                    break
            j += 1

    return {
        "name": name_m.group(1) if name_m else None,
        "path": path,
        "isMenu": is_menu,
        "groupId": group_id_m.group(1) if group_id_m else None,
        "group": group_m.group(1) if group_m else None,
        "children": children,
    }


def process_routes(routes: list[dict[str, Any]], parent_origin: str = "") -> list[dict[str, Any]]:
    """
    递归遍历路由树，收集「菜单叶子节点」的 originPath。

    逻辑镜像前端 processRoutes：
      - path 以 / 开头 → originPath = path
      - 否则 originPath = 父级 origin + '/' + path

    参数:
        routes: 当前层的路由节点列表
        parent_origin: 父节点算出的 originPath 前缀

    返回:
        叶子菜单列表，每项含 name、path（完整 originPath）、group、groupId
    """
    leaves: list[dict[str, Any]] = []

    for route in routes:
        path = route.get("path") or ""
        if path.startswith("/"):
            origin = path
        elif parent_origin:
            origin = f"{parent_origin}/{path}" if path else parent_origin
        else:
            origin = path

        children = route.get("children") or []
        # 仍有 isMenu 子节点的，当前节点不算「叶子菜单页」
        menu_children = [c for c in children if c.get("isMenu") and c.get("path")]

        if route.get("isMenu") and path and not menu_children:
            leaves.append(
                {
                    "name": route.get("name"),
                    "path": origin,
                    "group": route.get("group"),
                    "groupId": route.get("groupId"),
                }
            )

        if children:
            child_parent = origin if path else parent_origin
            # extend：把子树叶子合并进 leaves（递归）
            leaves.extend(process_routes(children, child_parent))

    return leaves


def _parse_exported_const(content: str, const_name: str) -> dict[str, Any] | None:
    """
    解析 routes.tsx 里单独 export 的路由常量，例如 PositionMaintenanceManagement。

    有些子树不在 _routes 数组里，而是 `export const Foo = { ... }` 形式引用。
    """
    marker = f"export const {const_name}"
    start = content.find(marker)
    if start < 0:
        return None
    brace = content.find("{", start)
    if brace < 0:
        return None
    depth = 0
    i = brace
    in_string = False
    string_char = ""
    escape = False
    while i < len(content):
        ch = content[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == string_char:
                in_string = False
            i += 1
            continue
        if ch in ("'", '"'):
            in_string = True
            string_char = ch
            i += 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                block = content[brace : i + 1]
                return _parse_route_block(block)
        i += 1
    return None


def build_aliases(entries: list[dict[str, Any]]) -> dict[str, str]:
    """
    构建「别名 → 正确 path」映射，方便用户说中文或写错 path 时仍能导航。

    例如：
      - 页面名「设备管理」→ 真实 path
      - 错误含 groupId 的路径 → 纠正后的 path
      - 口语「告警列表」→ 报警信息查询页
    """
    aliases: dict[str, str] = {}
    for entry in entries:
        name, path, group_id = entry.get("name"), entry.get("path"), entry.get("groupId")
        if not path:
            continue
        if name:
            aliases[name] = path
        if group_id:
            leaf = path.rsplit("/", 1)[-1]  # 最后一段 path 片段
            parent = path[: -(len(leaf) + 1)]
            wrong = f"{parent}/{group_id}/{leaf}"
            if wrong != path:
                aliases[wrong] = path

    # 下面用 next(生成器, None) 按 name 查找特定页面，再补常用口语别名
    equipment = next((e for e in entries if e.get("name") == "设备管理"), None)
    if equipment:
        aliases["/device_management"] = equipment["path"]
        aliases["/config_management/device_management"] = equipment["path"]
        aliases["设备管理"] = equipment["path"]

    alarm_q = next((e for e in entries if e.get("name") == "报警信息查询"), None)
    if alarm_q:
        aliases["告警列表"] = alarm_q["path"]
        aliases["告警查询"] = alarm_q["path"]

    alarm_s = next((e for e in entries if e.get("name") == "报警信息统计"), None)
    if alarm_s:
        aliases["告警统计"] = alarm_s["path"]

    facility = next((e for e in entries if e.get("name") == "设施管理"), None)
    if facility:
        aliases["设施管理"] = facility["path"]

    device_var = next((e for e in entries if e.get("name") == "设备变量"), None)
    if device_var:
        aliases["变量管理"] = device_var["path"]

    return aliases


def main() -> None:
    """
    主流程：若提供 PLATFORM_ROUTES_TSX 则重新提取；否则保留已有 navigation_routes.json。
    """
    if ROUTES_TSX is None or not ROUTES_TSX.exists():
        if OUT_JSON.exists():
            print(f"跳过导航提取（未设置 PLATFORM_ROUTES_TSX 或文件不存在），保留现有 {OUT_JSON}")
            return
        raise SystemExit("未找到 navigation_routes.json，且未设置有效的 PLATFORM_ROUTES_TSX")

    content = ROUTES_TSX.read_text(encoding="utf-8")
    start = content.find("export const _routes")
    if start < 0:
        raise SystemExit("未找到 export const _routes")
    bracket = content.find("[", start)
    end = content.find("\n];", bracket)
    section = content[bracket + 1 : end]

    tree: list[dict[str, Any]] = []
    for block in _split_route_objects(section):
        node = _parse_route_block(block)
        if node:
            tree.append(node)

    leaves = process_routes(tree)
    routes = [r for r in leaves if r.get("name") and r.get("path")]

    # 阵地维护管理子树（在 _routes 中以 PositionMaintenanceManagement 引用）
    pm = _parse_exported_const(content, "PositionMaintenanceManagement")
    if pm:
        pm_leaves = process_routes([pm], "/config_management")
        for item in pm_leaves:
            if item.get("name") and item.get("path"):
                if not any(r["path"] == item["path"] for r in routes):
                    routes.append(item)

    manifest = {
        "generatedAt": datetime.now(UTC).isoformat(),
        "rules": ROUTE_RULES,
        "routes": routes,
        "aliases": build_aliases(routes),
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Exported {len(routes)} navigation routes to {OUT_JSON}")
    if routes:
        equip = next((r for r in routes if r["name"] == "设备管理"), None)
        if equip:
            print(f"  设备管理 -> {equip['path']}")
        fac = next((r for r in routes if r["name"] == "设施管理"), None)
        if fac:
            print(f"  设施管理 -> {fac['path']}")


if __name__ == "__main__":
    main()
