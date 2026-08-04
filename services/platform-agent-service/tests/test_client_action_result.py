"""P2-2：client_action 执行回执 API。"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.client_action_result import ClientActionResultBody, report_client_action_result


@pytest.mark.asyncio
async def test_report_client_action_result_writes_audit():
    body = ClientActionResultBody(
        action="navigate",
        ok=True,
        skipped=False,
        path="/facility",
        summary="宿主已导航",
    )
    append = MagicMock()
    with (
        patch(
            "app.api.client_action_result.get_current_user_id",
            new_callable=AsyncMock,
            return_value="u1",
        ),
        patch("app.api.client_action_result.is_postgres_enabled", return_value=False),
        patch("app.api.client_action_result.audit_store") as store,
    ):
        store.append = append
        resp = await report_client_action_result("thread-1", body, authorization="Bearer x")

    assert resp["code"] == 0
    assert resp["data"]["action"] == "navigate"
    assert resp["data"]["skipped"] is False
    append.assert_called_once()
    assert append.call_args.kwargs["event_type"] == "client_action_result"
    assert append.call_args.kwargs["thread_id"] == "thread-1"
    assert append.call_args.kwargs["payload_summary"]["path"] == "/facility"


@pytest.mark.asyncio
async def test_report_skipped_open_modal():
    body = ClientActionResultBody(
        action="openModal",
        ok=True,
        skipped=True,
        modal="alarmDetail",
        summary="无宿主跳过",
    )
    append = MagicMock()
    with (
        patch(
            "app.api.client_action_result.get_current_user_id",
            new_callable=AsyncMock,
            return_value="u1",
        ),
        patch("app.api.client_action_result.is_postgres_enabled", return_value=False),
        patch("app.api.client_action_result.audit_store") as store,
    ):
        store.append = append
        resp = await report_client_action_result("t2", body)

    assert resp["code"] == 0
    assert resp["data"]["skipped"] is True
    assert append.call_args.kwargs["payload_summary"]["skipped"] is True


@pytest.mark.asyncio
async def test_report_rejects_empty_thread():
    body = ClientActionResultBody(action="toast", ok=True)
    with patch(
        "app.api.client_action_result.get_current_user_id",
        new_callable=AsyncMock,
        return_value="u1",
    ):
        resp = await report_client_action_result("  ", body)
    assert resp["code"] == 40071


@pytest.mark.asyncio
async def test_report_forbidden_when_not_owner():
    body = ClientActionResultBody(action="navigate", ok=True, path="/x")
    with (
        patch(
            "app.api.client_action_result.get_current_user_id",
            new_callable=AsyncMock,
            return_value="u1",
        ),
        patch("app.api.client_action_result.is_postgres_enabled", return_value=True),
        patch("app.api.client_action_result.can_read_thread", return_value=False),
    ):
        resp = await report_client_action_result("other-thread", body)
    assert resp["code"] == 40471
