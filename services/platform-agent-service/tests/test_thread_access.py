"""会话读权限校验单测。"""

from unittest.mock import patch

from app.api.thread_access import can_read_thread


class TestCanReadThread:
    def test_memory_mode_always_allows(self):
        with patch("app.api.thread_access.is_postgres_enabled", return_value=False):
            assert can_read_thread("user_abc", "thread-1") is True

    def test_postgres_owned_session(self):
        with (
            patch("app.api.thread_access.is_postgres_enabled", return_value=True),
            patch(
                "app.api.thread_access.session_store.has_thread",
                return_value=True,
            ),
        ):
            assert can_read_thread("user_abc", "thread-1") is True

    def test_postgres_rejects_checkpoint_only_fallback(self):
        """会话索引缺失时不得凭 checkpoint 放行，避免越权与删会话后回源。"""
        with (
            patch("app.api.thread_access.is_postgres_enabled", return_value=True),
            patch(
                "app.api.thread_access.session_store.has_thread",
                return_value=False,
            ),
        ):
            assert can_read_thread("user_abc", "thread-1") is False

    def test_postgres_empty_thread_denied(self):
        with (
            patch("app.api.thread_access.is_postgres_enabled", return_value=True),
            patch(
                "app.api.thread_access.session_store.has_thread",
                return_value=False,
            ),
        ):
            assert can_read_thread("user_abc", "thread-1") is False


class TestStableUserId:
    def test_same_token_same_user_id(self):
        import asyncio
        import hashlib

        from app.middleware.auth import get_current_user_id, resolve_user_id_from_token

        token = "Bearer eyJ.test.token"

        async def _run():
            return await get_current_user_id(token)

        uid1 = asyncio.run(_run())
        uid2 = asyncio.run(_run())
        assert uid1 == uid2
        assert resolve_user_id_from_token(token) == uid1
        digest = hashlib.sha256(b"eyJ.test.token").hexdigest()[:8]
        assert uid1 == f"user_{digest}"
