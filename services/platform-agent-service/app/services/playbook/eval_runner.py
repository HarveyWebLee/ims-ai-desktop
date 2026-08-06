"""Playbook 固定用例评测（离线；不调 LLM、不改运行时主链）。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_SERVICE_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CASES_PATH = _SERVICE_ROOT / "eval" / "playbook_cases.json"


@dataclass(frozen=True)
class CaseResult:
    """单用例结果。"""

    case_id: str
    ok: bool
    errors: tuple[str, ...]


def load_cases(path: Path | None = None) -> list[dict[str, Any]]:
    """加载 JSON 用例文件。"""
    cases_path = path or DEFAULT_CASES_PATH
    raw = json.loads(cases_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"用例文件须为 JSON object: {cases_path}")
    cases = raw.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError(f"缺少非空 cases 列表: {cases_path}")
    return [c for c in cases if isinstance(c, dict)]


def evaluate_case(case: dict[str, Any]) -> CaseResult:
    """对单条用例执行 playbook 匹配 + 工具子集断言。"""
    from app.config import settings
    from app.services.playbook.service import clear_playbook_cache, match_playbooks
    from app.services.tool_subset import infer_domains_from_text, select_tool_subset

    case_id = str(case.get("id") or case.get("message") or "unknown")
    message = str(case.get("message") or "").strip()
    errors: list[str] = []
    if not message:
        return CaseResult(case_id=case_id, ok=False, errors=("message 为空",))

    prev_enabled = settings.agent_playbook_enabled
    prev_dir = settings.agent_playbook_dir
    settings.agent_playbook_enabled = True
    settings.agent_playbook_dir = ""
    clear_playbook_cache()

    recent = case.get("recent_user_messages") or []
    if not isinstance(recent, list):
        recent = []
    recent_msgs = [str(x) for x in recent]

    try:
        matches = match_playbooks(message, recent_user_messages=recent_msgs)
        matched_ids = [m.playbook.id for m in matches]

        expect_playbook = case.get("expect_playbook")
        if expect_playbook:
            expected = str(expect_playbook)
            if expected not in matched_ids:
                errors.append(f"playbook 未命中: expect={expected} got={matched_ids}")

        forbid_playbook = case.get("forbid_playbook")
        if forbid_playbook:
            forbidden = str(forbid_playbook)
            if forbidden in matched_ids:
                errors.append(f"playbook 不应命中: forbid={forbidden} got={matched_ids}")

        expect_domains = case.get("expect_domains")
        if isinstance(expect_domains, list):
            domains = infer_domains_from_text(message, *recent_msgs[-4:])
            expected_set = {str(d) for d in expect_domains}
            if expected_set:
                missing = sorted(expected_set - set(domains))
                if missing:
                    errors.append(f"domains 漏绑: missing={missing} got={sorted(domains)}")
            elif domains:
                errors.append(f"domains 应为空: got={sorted(domains)}")

        expect_tools = case.get("expect_tools_include") or []
        forbid_tools = case.get("forbid_tools") or []
        if expect_tools or forbid_tools:
            available = case.get("available_tools")
            available_names = (
                frozenset(str(n) for n in available) if isinstance(available, list) else None
            )
            run_mode = str(case.get("run_mode") or "confirm")
            subset = select_tool_subset(
                run_mode=run_mode,
                message=message,
                recent_user_messages=recent_msgs,
                available_names=available_names,
            )
            missing_tools = [str(t) for t in expect_tools if str(t) not in subset.tool_names]
            if missing_tools:
                errors.append(
                    f"工具子集漏绑: missing={missing_tools} got={sorted(subset.tool_names)}"
                )
            leaked = [str(t) for t in forbid_tools if str(t) in subset.tool_names]
            if leaked:
                errors.append(f"工具子集误绑写工具: leaked={leaked}")

        expect_steps = case.get("expect_step_keywords") or []
        if expect_steps and matches:
            body = "\n".join(m.playbook.body for m in matches)
            for kw in expect_steps:
                if str(kw) not in body:
                    errors.append(f"playbook 正文缺步骤关键词: {kw!r}")
    finally:
        settings.agent_playbook_enabled = prev_enabled
        settings.agent_playbook_dir = prev_dir
        clear_playbook_cache()

    return CaseResult(case_id=case_id, ok=not errors, errors=tuple(errors))


def run_eval(cases_path: Path | None = None) -> list[CaseResult]:
    """跑完全部用例。"""
    return [evaluate_case(c) for c in load_cases(cases_path)]
