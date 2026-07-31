"""
平台页面导航服务：模糊匹配、路径解析（与前端 routes.tsx originPath 对齐）。

文件职责
--------
为 ``navigate_to`` 客户端工具提供「用户口语 → 平台 URL 路径」的解析能力。
LLM 传入原话（如「打开设备管理」）后，本模块用 navigation_routes.json
做模糊匹配：唯一命中则自动跳转；多个候选则返回列表供 HITL 选择。

在 Agent 流程中的位置
--------------------
    navigate_to 工具 / preflight
      → pick_navigation_path(query) 或 match_navigation_routes
      → path 唯一：直接 client_action 跳转
      → 多候选：ask_params HITL 下拉
    system prompt 注入：get_navigation_rules_for_prompt /
      format_navigation_hints_for_prompt

如何被调用
----------
- 工具层：``app.tools`` 中 navigate 相关 handler
- Prompt 组装：``prompt_assembly`` 注入路由规范与常用页
- 数据源：``app/data/navigation_routes.json``（前端路由导出或手工维护）

关键概念
--------
- originPath：浏览器地址栏路径，navigate_to 必须用此格式（禁止组件 filePath）
- 设施管理 ≠ 设备管理（``_facility_device_penalty`` 降权，避免误跳）
"""

from __future__ import annotations

# ── 标准库 ──
import json
import logging
from dataclasses import dataclass  # 数据类装饰器，自动生成 __init__ 等
from difflib import SequenceMatcher  # 字符串相似度计算
from functools import lru_cache
from pathlib import Path
from typing import Any

from contracts.paths import mcp_data_dir

logger = logging.getLogger(__name__)


def _manifest_path() -> Path:
    return mcp_data_dir() / "navigation_routes.json"


# 纳入候选的最低匹配分；唯一候选且高于此分可自动跳转
MIN_CANDIDATE_SCORE = 45.0
# 视为「完全匹配」的分数
EXACT_MATCH_SCORE = 100.0

# 内置别名兜底（manifest 缺失或别名未覆盖时使用）
_FALLBACK_ALIASES: dict[str, str] = {
    "变量管理": "/config_management/config/var",
    "设备管理": "/config_management/config/equipment_manage",
    "设施管理": "/config_management/positional_management/facility_management",
    "告警列表": "/config_management/config/alarm_info_query",
    "告警查询": "/config_management/config/alarm_info_query",
    "告警统计": "/config_management/config/alarm_info_statistics",
    "/device_management": "/config_management/config/equipment_manage",
    "/config_management/device_management": "/config_management/config/equipment_manage",
    "/config_management/config/monitor_equipment/equipment_manage": (
        "/config_management/config/equipment_manage"
    ),
    "/config_management/config/alarm_query_statistics/alarm_info_query": (
        "/config_management/config/alarm_info_query"
    ),
}

_FALLBACK_RULES = """## 平台路由路径规范（navigate_to 必须遵守）

1. 只使用 originPath（浏览器地址栏路径），禁止使用组件 filePath。
2. originPath 不含 meta.groupId（groupId 仅用于组件目录，不出现在 URL）。
3. 子级路径 = 父级 originPath + '/' + 当前 path 段。
4. **设施管理** 与 **设备管理** 是不同页面，禁止混淆。"""


@dataclass(frozen=True)
class NavigationMatch:
    """
    单条导航匹配结果（不可变数据类，frozen=True 禁止修改字段）。

    属性:
        name: 页面中文名
        path: originPath
        score: 匹配分数 0～100
        group: 所属菜单分组
        match_reason: 匹配原因（exact_name / fuzzy / alias 等）
    """

    name: str
    path: str
    score: float
    group: str | None = None
    match_reason: str = ""


@lru_cache(maxsize=1)
def _load_manifest() -> dict[str, Any]:
    """
    加载 navigation_routes.json（进程内缓存）。

    返回:
        含 rules、routes、aliases 的 dict；失败时用内置兜底
    """
    if not _manifest_path().exists():
        logger.warning("navigation_routes.json 不存在，使用内置兜底")
        return {
            "rules": _FALLBACK_RULES,
            "routes": [],
            "aliases": dict(_FALLBACK_ALIASES),
        }
    try:
        return json.loads(_manifest_path().read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("读取 navigation_routes.json 失败: %s", exc)
        return {
            "rules": _FALLBACK_RULES,
            "routes": [],
            "aliases": dict(_FALLBACK_ALIASES),
        }


def get_navigation_aliases() -> dict[str, str]:
    """
    获取全部导航别名（内置 + manifest 合并）。

    返回:
        {别名或旧路径: originPath} 字典
    """
    manifest = _load_manifest()
    aliases = dict(_FALLBACK_ALIASES)
    aliases.update(manifest.get("aliases") or {})  # update 合并后者覆盖前者
    return aliases


def _get_routes_list() -> list[dict[str, Any]]:
    """从 manifest 取 routes 列表副本。"""
    return list(_load_manifest().get("routes") or [])


# 使用者口语里常见的动作前缀 / 页面后缀，归一化后再做模糊匹配或别名命中
_QUERY_PREFIXES = (
    "请帮我打开",
    "帮我打开",
    "请打开",
    "麻烦打开",
    "请进入",
    "帮我进入",
    "请跳转",
    "帮我跳转",
    "跳转到",
    "打开",
    "进入",
    "跳转",
    "前往",
    "访问",
)
_QUERY_SUFFIXES = ("模块", "页面", "页", "功能", "菜单")


def _normalize_text(text: str) -> str:
    """
    将「打开变量管理页面」等口语归一化为「变量管理」再参与匹配。

    参数:
        text: 原始查询文本

    返回:
        小写、去掉动作前缀和页面后缀后的核心词
    """
    text = (text or "").strip().lower()
    # 反复剥离末尾后缀，兼容「变量管理功能页面」等叠词
    changed = True
    while changed and text:
        changed = False
        for suffix in _QUERY_SUFFIXES:
            if text.endswith(suffix):
                text = text[: -len(suffix)].strip()
                changed = True
                break
    # 按长度优先剥离动作前缀，避免「跳转到」被拆成「转到」
    for prefix in sorted(_QUERY_PREFIXES, key=len, reverse=True):
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()
            break
    return text


def _normalize_query(query: str) -> str:
    """对外归一化入口，当前与 _normalize_text 相同。"""
    return _normalize_text(query)


def _find_route_by_path(path: str) -> dict[str, Any] | None:
    """在 routes 列表中按 path 精确查找一条路由记录。"""
    for route in _get_routes_list():
        if route.get("path") == path:
            return route
    return None


def _facility_device_penalty(query: str, name: str) -> float:
    """
    「设施」「设备」互斥时降权，避免误匹配。

    返回:
        乘数，1.0 表示不降权，0.55 表示分数打 55 折
    """
    q_has_facility = "设施" in query
    q_has_device = "设备" in query
    n_has_facility = "设施" in name
    n_has_device = "设备" in name
    if q_has_facility and n_has_device and not n_has_facility:
        return 0.55
    if q_has_device and n_has_facility and not n_has_device:
        return 0.55
    return 1.0


def _score_name_against_query(
    query: str,
    name: str,
    *,
    group: str | None = None,
) -> tuple[float, str]:
    """
    计算页面名称与用户查询的匹配分数。

    参数:
        query: 用户查询（已或可归一化）
        name: 页面中文名
        group: 可选菜单分组名

    返回:
        (分数, 匹配原因) 元组
    """
    qn = _normalize_query(query)
    nn = _normalize_text(name)

    if not qn or not nn:
        return 0.0, ""

    if qn == nn:
        return EXACT_MATCH_SCORE, "exact_name"

    # SequenceMatcher.ratio() 返回 0～1 的相似度
    ratio = SequenceMatcher(None, qn, nn).ratio()
    if qn in nn:
        ratio = max(ratio, 0.88 + 0.12 * len(qn) / max(len(nn), 1))
    elif nn in qn:
        ratio = max(ratio, 0.85)

    if group:
        gn = _normalize_text(group)
        if qn in gn or gn in qn:
            ratio = max(ratio, 0.75)

    score = ratio * 90.0
    score *= _facility_device_penalty(qn, nn)
    return min(EXACT_MATCH_SCORE - 0.01, score), "fuzzy"


def _score_path_against_query(query: str, path: str) -> tuple[float, str]:
    """
    计算 URL 路径与用户查询的匹配分数（含 path 末段 leaf 匹配）。

    返回:
        (分数, 匹配原因) 元组
    """
    qn = _normalize_query(query)
    if not qn:
        return 0.0, ""

    normalized_path = path.rstrip("/")
    if qn == normalized_path or qn == normalized_path.lstrip("/"):
        return EXACT_MATCH_SCORE, "exact_path"

    leaf = normalized_path.rsplit("/", 1)[-1]  # 取最后一段路径
    leaf_readable = leaf.replace("_", " ")
    if qn == leaf or qn == _normalize_text(leaf):
        return EXACT_MATCH_SCORE - 1, "exact_leaf"

    ratio = SequenceMatcher(None, qn, _normalize_text(leaf_readable)).ratio()
    return min(85.0, ratio * 85), "path_fuzzy"


def match_navigation_routes(query: str, *, limit: int = 10) -> list[NavigationMatch]:
    """
    模糊匹配平台菜单页，按匹配度降序。

    完全匹配（100 分）优先；设施/设备等同名歧义通过降权与多选 HITL 处理。

    参数:
        query: 用户口语或路径
        limit: 最多返回候选数

    返回:
        NavigationMatch 列表，按 score 降序
    """
    q = (query or "").strip()
    if not q:
        return []

    routes = _get_routes_list()
    aliases = get_navigation_aliases()
    best_by_path: dict[str, NavigationMatch] = {}  # 同 path 只保留最高分

    def _upsert(match: NavigationMatch) -> None:
        """内部函数：更新 best_by_path，仅保留更高分。"""
        if match.score < MIN_CANDIDATE_SCORE:
            return
        prev = best_by_path.get(match.path)
        if prev is None or match.score > prev.score:
            best_by_path[match.path] = match

    for route in routes:
        name = str(route.get("name") or "")
        path = str(route.get("path") or "")
        group = route.get("group")
        if not name or not path:
            continue
        score, reason = _score_name_against_query(q, name, group=group)
        _upsert(
            NavigationMatch(name=name, path=path, score=score, group=group, match_reason=reason)
        )
        p_score, p_reason = _score_path_against_query(q, path)
        if p_score > score:
            _upsert(
                NavigationMatch(
                    name=name,
                    path=path,
                    score=p_score,
                    group=group,
                    match_reason=p_reason,
                )
            )

    # 别名表：以 / 开头的是「旧路径 → originPath」；否则是「中文名 → path」
    for alias, path in aliases.items():
        if alias.startswith("/"):
            # 旧 path 精确命中才升 100 分（避免部分路径误伤）
            if q == alias or q.rstrip("/") == alias:
                route = _find_route_by_path(path)
                name = str(route.get("name") if route else path)
                _upsert(
                    NavigationMatch(
                        name=name,
                        path=path,
                        score=EXACT_MATCH_SCORE,
                        group=route.get("group") if route else None,
                        match_reason="alias_path",
                    )
                )
            continue

        route = _find_route_by_path(path)
        name = str(route.get("name") if route else alias)
        group = route.get("group") if route else None
        score, reason = _score_name_against_query(q, alias, group=group)
        if score >= MIN_CANDIDATE_SCORE:
            _upsert(
                NavigationMatch(
                    name=name,
                    path=path,
                    score=score,
                    group=group,
                    match_reason=f"alias_{reason}",
                )
            )

    return sorted(
        best_by_path.values(),
        key=lambda m: (-m.score, m.name),  # 先按分数降序，再按名称
    )[:limit]


def resolve_navigation_path(path: str) -> str:
    """
    将已知错误 path / 别名解析为 originPath（不含模糊多选）。

    参数:
        path: 可能是别名、旧路径或已正确的 originPath

    返回:
        规范化后的 originPath
    """
    raw = (path or "").strip()
    if not raw:
        return raw

    aliases = get_navigation_aliases()
    if raw in aliases:
        return aliases[raw]
    trimmed = raw.rstrip("/")
    if trimmed in aliases:
        return aliases[trimmed]

    # 已是合法 originPath
    for route in _get_routes_list():
        if route.get("path") == trimmed:
            return trimmed

    return raw if raw.startswith("/") else f"/{raw}"


def pick_navigation_path(query: str) -> tuple[str | None, list[NavigationMatch]]:
    """
    根据匹配结果决定最终 path。

    决策规则:
        - 唯一完全匹配 → 自动返回 path
        - 唯一候选（分数达标）→ 自动返回 path
        - 多个候选 → 返回 (None, 列表)，由调用方走 HITL

    返回:
        (最终 path 或 None, 全部达标候选列表)
    """
    matches = match_navigation_routes(query)
    candidates = [m for m in matches if m.score >= MIN_CANDIDATE_SCORE]

    if not candidates:
        return None, []

    # 唯一「满分」命中 → 自动跳（如别名精确）
    exact = [m for m in candidates if m.score >= EXACT_MATCH_SCORE]
    if len(exact) == 1:
        return exact[0].path, candidates

    # 仅一个达标候选 → 也自动跳；多个 → 交给 HITL
    if len(candidates) == 1:
        return candidates[0].path, candidates

    return None, candidates


def format_match_option_label(match: NavigationMatch) -> str:
    """
    HITL 下拉项展示文案。

    参数:
        match: 单条匹配结果

    返回:
        如「设备管理（配置管理）· 匹配度 92%」
    """
    label = match.name
    if match.group:
        label = f"{label}（{match.group}）"
    return f"{label} · 匹配度 {int(match.score)}%"


def get_navigation_route_hints(limit: int = 24) -> list[tuple[str, str]]:
    """
    获取常用页面 (名称, path) 列表，供 system prompt 注入。

    参数:
        limit: 最多条数

    返回:
        [(页面名, originPath), ...]
    """
    manifest = _load_manifest()
    routes = manifest.get("routes") or []
    preferred_names = (
        "设备管理",
        "设施管理",
        "报警信息查询",
        "报警信息统计",
        "历史数据查询",
        "数采服务器",
    )
    by_name = {r.get("name"): r.get("path") for r in routes if r.get("name") and r.get("path")}
    hints: list[tuple[str, str]] = []
    for name in preferred_names:
        if name in by_name:
            hints.append((name, by_name[name]))
    for r in routes:
        name, path = r.get("name"), r.get("path")
        if not name or not path:
            continue
        if (name, path) not in hints:
            hints.append((name, path))
        if len(hints) >= limit:
            break
    return hints


def get_navigation_rules_for_prompt() -> str:
    """
    获取 navigate_to 路由规范 Markdown（含 manifest rules + 补充说明）。

    返回:
        多行 Markdown 字符串
    """
    manifest = _load_manifest()
    base = str(manifest.get("rules") or _FALLBACK_RULES)
    extra = (
        "\n6. **navigate_to 的 path 参数**：传使用者原话（如「设施管理」），"
        "工具会自动匹配；仅一个完全匹配时直接跳转，多个匹配时由使用者选择。"
        "\n7. **设施管理** ≠ **设备管理**，不得混用。"
    )
    return base + extra


def format_navigation_hints_for_prompt() -> str:
    """
    将常用路由格式化为 Prompt 列表项。

    返回:
        如 "- 设备管理：`/config_management/config/equipment_manage`"
    """
    hint_lines = [f"- {name}：`{path}`" for name, path in get_navigation_route_hints()]
    return "\n".join(hint_lines)
