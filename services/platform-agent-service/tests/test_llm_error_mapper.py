"""llm_error_mapper 单测"""

from __future__ import annotations

from app.services.llm_error_mapper import classify_llm_exception, format_llm_error_event


class TestLlmErrorMapper:
    def test_dashscope_free_quota(self):
        exc = Exception(
            "Error code: 403 - {'error': {'message': 'The free quota has been exhausted. "
            "To continue accessing the model on a paid basis, please complete your payment "
            "information', 'type': 'AllocationQuota.FreeTierOnly', 'code': "
            "'AllocationQuota.FreeTierOnly'}, 'id': 'chatcmpl-x', 'request_id': 'chatcmpl-x'}"
        )
        kind, status, err_type = classify_llm_exception(exc)
        assert kind == "quota_exhausted"
        assert status == 403
        assert "allocationquota" in (err_type or "")

        event = format_llm_error_event(exc)
        assert event["code"] == 50002
        assert "免费额度" in event["message"]
        assert event["data"]["kind"] == "quota_exhausted"
        assert event["data"]["hint"]
        assert isinstance(event["data"], dict)

    def test_auth_error(self):
        exc = Exception("Error code: 401 - {'error': {'message': 'Invalid API Key'}}")
        kind, status, _ = classify_llm_exception(exc)
        assert kind == "auth"
        assert status == 401

    def test_rate_limit(self):
        exc = Exception("Error code: 429 - {'error': {'message': 'Rate limit exceeded'}}")
        kind, status, _ = classify_llm_exception(exc)
        assert kind == "rate_limit"
        assert status == 429

    def test_unknown_fallback_message(self):
        exc = Exception("something weird happened")
        event = format_llm_error_event(exc, fallback_message="自定义失败")
        assert event["message"] == "自定义失败"
        assert event["data"]["kind"] == "unknown"

    def test_format_error_assistant_content_includes_hint(self):
        from app.services.llm_error_mapper import format_error_assistant_content

        event = format_llm_error_event(
            Exception(
                "Error code: 403 - {'error': {'message': 'The free quota has been exhausted.', "
                "'type': 'AllocationQuota.FreeTierOnly'}}"
            )
        )
        text = format_error_assistant_content(event)
        assert text.startswith("⚠️")
        assert "免费额度" in text
        assert "按量付费" in text
        assert "\n\n" in text

    def test_format_error_assistant_content_none_payload(self):
        from app.services.llm_error_mapper import format_error_assistant_content

        text = format_error_assistant_content(None)
        assert text.startswith("⚠️")
        assert "失败" in text
