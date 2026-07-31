"""query_devices 设备查询工具单测"""

from __future__ import annotations

from unittest.mock import patch

from platform_mcp.runtime.tools.device import (
    _map_online_status_token,
    build_device_list_payload,
    query_devices,
)


class TestOnlineStatusMap:
    def test_chinese_online(self):
        assert _map_online_status_token("在线") == 1

    def test_chinese_offline(self):
        assert _map_online_status_token("离线") == 0

    def test_numeric(self):
        assert _map_online_status_token("2") == 2

    def test_invalid(self):
        assert _map_online_status_token("unknown") is None


class TestBuildDeviceListPayload:
    def test_combined_filters(self):
        payload = build_device_list_payload(
            search="泵",
            device_name="1号泵",
            device_code="DEV001",
            online_status=1,
        )
        assert payload["search"] == "泵"
        assert payload["deviceName"] == "1号泵"
        assert payload["deviceCode"] == "DEV001"
        assert payload["onlineStatus"] == 1
        assert payload["page"] == 1


class TestQueryDevices:
    def test_success_summary(self):
        mock_data = {
            "total": 2,
            "records": [
                {
                    "deviceCode": "D1",
                    "deviceName": "设备一",
                    "onlineStatus": 1,
                    "regionName": "A区",
                },
                {
                    "deviceCode": "D2",
                    "deviceName": "设备二",
                    "onlineStatus": 0,
                },
            ],
        }
        with patch(
            "platform_mcp.runtime.tools.device.call_platform_api",
            return_value=mock_data,
        ):
            raw = query_devices.invoke({"search": "设备"})
        import json

        body = json.loads(raw)
        assert body["ok"] is True
        assert "2 台设备" in body["summary"]
        assert len(body["data"]["items"]) == 2

    def test_invalid_online_status(self):
        raw = query_devices.invoke({"online_status": "无效状态"})
        import json

        body = json.loads(raw)
        assert body["ok"] is False
        assert "在线状态无效" in body["summary"]

    def test_platform_error(self):
        from platform_mcp.runtime.platform_client import PlatformApiError

        with patch(
            "platform_mcp.runtime.tools.device.call_platform_api",
            side_effect=PlatformApiError("平台不可用"),
        ):
            raw = query_devices.invoke({})
        import json

        body = json.loads(raw)
        assert body["ok"] is False
        assert "平台不可用" in body["summary"]
