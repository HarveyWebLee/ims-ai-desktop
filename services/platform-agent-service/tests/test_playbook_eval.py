"""Playbook 自动评测脚本与固定用例。"""

from __future__ import annotations

from pathlib import Path

from app.services.playbook.eval_runner import DEFAULT_CASES_PATH, evaluate_case, run_eval


def test_playbook_eval_default_cases_pass() -> None:
    results = run_eval(DEFAULT_CASES_PATH)
    failed = [r for r in results if not r.ok]
    assert not failed, "\n".join(f"{r.case_id}: {list(r.errors)}" for r in failed)


def test_condition_colloquial_open_domains() -> None:
    result = evaluate_case(
        {
            "id": "local-colloquial",
            "message": "有告警就把东门开了",
            "expect_domains": ["alarm", "device"],
            "expect_tools_include": ["query_alarms", "send_device_cmd"],
            "available_tools": [
                "query_alarms",
                "send_device_cmd",
                "retrieve_knowledge",
            ],
        }
    )
    assert result.ok, result.errors


def test_eval_cases_file_exists() -> None:
    assert Path(DEFAULT_CASES_PATH).is_file()
