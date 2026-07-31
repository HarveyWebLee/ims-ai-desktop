"""设备工具包单测：详情 / 变量 / 指令下发 / Client 跳转"""

from __future__ import annotations

from unittest.mock import patch

from platform_mcp.runtime.platform_client import PlatformApiError
from platform_mcp.runtime.tools.client_actions import open_device_detail
from platform_mcp.runtime.tools.device import (
    _build_send_cmd_payload,
    _build_var_list_request,
    _check_device_cmd_preconditions,
    _map_device_detail,
    _resolve_device_code,
    _resolve_writable_variable_name,
    get_device_detail,
    query_device_variables,
    send_device_cmd,
)


class TestMapDeviceDetail:
    def test_masks_password(self):
        detail = _map_device_detail(
            {
                "deviceCode": "D1",
                "deviceName": "泵1",
                "password": "secret",
                "onlineStatus": 1,
            }
        )
        assert detail["password"] == "***"
        assert detail["deviceCode"] == "D1"

    def test_maps_device_status_as_enable_label(self):
        """平台 deviceStatus 为启用态码，需映射可读标签。"""
        detail = _map_device_detail(
            {
                "deviceCode": "D1",
                "deviceName": "门禁",
                "deviceStatus": 1,
                "onlineStatus": 1,
            }
        )
        assert detail["deviceStatus"] == 1
        assert detail["deviceStatusLabel"] == "启用"
        assert detail["enableStatus"] == 1
        assert detail["enableStatusLabel"] == "启用"
        assert detail["onlineStatusLabel"] == "在线"


class TestResolveDeviceCode:
    @patch("platform_mcp.runtime.tools.device.call_platform_api")
    def test_by_code(self, mock_api):
        mock_api.return_value = {"deviceCode": "D1", "deviceName": "泵1"}
        code, record, err = _resolve_device_code(device_code="D1")
        assert err is None
        assert record is not None
        assert code == "D1"
        assert record["deviceName"] == "泵1"

    @patch("platform_mcp.runtime.tools.device.call_platform_api")
    def test_by_name_single_match(self, mock_api):
        mock_api.return_value = {
            "total": 1,
            "records": [{"deviceCode": "D2", "deviceName": "泵2"}],
        }
        code, record, err = _resolve_device_code(device_name="泵2")
        assert err is None
        assert code == "D2"

    @patch("platform_mcp.runtime.tools.device.call_platform_api")
    def test_by_name_no_match(self, mock_api):
        mock_api.return_value = {"total": 0, "records": []}
        code, record, err = _resolve_device_code(device_name="不存在")
        assert code is None
        assert "未找到" in (err or "")


class TestGetDeviceDetail:
    @patch(
        "platform_mcp.runtime.tool_preflight.ensure_tool_args", side_effect=lambda _n, args: args
    )
    @patch("platform_mcp.runtime.tools.device._resolve_device_code")
    def test_success(self, mock_resolve, _ensure):
        mock_resolve.return_value = (
            "D1",
            {
                "deviceCode": "D1",
                "deviceName": "泵1",
                "onlineStatus": 1,
                "regionName": "A区",
            },
            None,
        )
        raw = get_device_detail.invoke({"device_code": "D1"})
        assert '"ok": true' in raw or '"ok":true' in raw.replace(" ", "")
        assert "泵1" in raw


class TestQueryDeviceVariables:
    @patch(
        "platform_mcp.runtime.tool_preflight.ensure_tool_args", side_effect=lambda _n, args: args
    )
    @patch(
        "platform_mcp.runtime.tools.device._resolve_device_code",
        return_value=("D1", {"deviceCode": "D1"}, None),
    )
    @patch("platform_mcp.runtime.tools.device.call_platform_api")
    def test_list_variables(self, mock_api, _resolve, _ensure):
        mock_api.return_value = [
            {"varName": "switch", "showName": "开关", "isWrite": 1},
            {"varName": "temp", "showName": "温度", "isWrite": 0},
        ]
        raw = query_device_variables.invoke({"device_code": "D1"})
        assert "switch" in raw
        assert "2" in raw or "共查询到 2" in raw
        mock_api.assert_called_once()
        assert mock_api.call_args.kwargs.get("path") == "/device/getVarListByCode"

    @patch(
        "platform_mcp.runtime.tool_preflight.ensure_tool_args", side_effect=lambda _n, args: args
    )
    @patch(
        "platform_mcp.runtime.tools.device._resolve_device_code",
        return_value=("D1", {"deviceCode": "D1"}, None),
    )
    @patch("platform_mcp.runtime.tools.device.call_platform_api")
    def test_filter_by_show_name_uses_server_field(self, mock_api, _resolve, _ensure):
        mock_api.return_value = [
            {"varName": "status_door_open", "showName": "门控制状态", "isWrite": 1},
        ]
        query_device_variables.invoke({"device_code": "D1", "var_name": "门控制状态"})
        assert mock_api.call_args.kwargs["data"].get("showName") == "门控制状态"

    @patch(
        "platform_mcp.runtime.tool_preflight.ensure_tool_args", side_effect=lambda _n, args: args
    )
    @patch("platform_mcp.runtime.tools.device._resolve_device_code")
    @patch("platform_mcp.runtime.tools.device.call_platform_api")
    def test_list_variables_by_device_name(self, mock_api, mock_resolve, _ensure):
        """仅有 device_name 时应先解析编码再查变量。"""
        mock_resolve.return_value = ("D1", {"deviceCode": "D1"}, None)
        mock_api.return_value = [
            {"varName": "switch", "showName": "开关", "isWrite": 1},
        ]
        raw = query_device_variables.invoke({"device_name": "B口门禁"})
        assert "switch" in raw
        mock_resolve.assert_called_once()
        assert mock_resolve.call_args.kwargs.get("device_name") == "B口门禁"
        assert mock_resolve.call_args.kwargs.get("hitl_tool") == "query_device_variables"
        assert mock_api.call_args.kwargs.get("path") == "/device/getVarListByCode"
        assert mock_api.call_args.kwargs["data"].get("deviceCode") == "D1"


class TestResolveVariableName:
    @patch("platform_mcp.runtime.tools.device.call_platform_api")
    def test_show_name_server_filter_single_match(self, mock_api):
        """服务端 showName 筛选唯一命中时直接采用 varName。"""
        mock_api.return_value = [
            {"varName": "status_door_open", "showName": "门控制状态", "isWrite": 1},
        ]
        vn, err = _resolve_writable_variable_name("D1", "门控制状态")
        assert err is None
        assert vn == "status_door_open"
        assert mock_api.call_args.kwargs["data"].get("showName") == "门控制状态"

    @patch("platform_mcp.runtime.tools.device.call_platform_api")
    def test_allows_non_writable_variable(self, mock_api):
        """显式指定变量时不校验 isWrite，只读变量也可解析下发。"""
        mock_api.return_value = [
            {"varName": "at_control", "showName": "控制", "isWrite": 0},
            {"varName": "temp", "showName": "温度", "isWrite": 0},
        ]
        vn, err = _resolve_writable_variable_name("FJ103", "at_control")
        assert err is None
        assert vn == "at_control"

    @patch("platform_mcp.runtime.tools.device.call_platform_api")
    def test_passthrough_when_list_empty(self, mock_api):
        """变量列表为空时仍采用用户输入的 varName，不本地拦截。"""
        mock_api.return_value = []
        vn, err = _resolve_writable_variable_name("FJ103", "at_control")
        assert err is None
        assert vn == "at_control"

    @patch("platform_mcp.runtime.tools.device.call_platform_api")
    def test_show_name_server_fuzzy_filter_exact_narrow(self, mock_api):
        """平台 showName 模糊返回多条时，精确 showName 收窄为唯一 varName。"""
        mock_api.return_value = [
            {"varName": "button_cut", "showName": "按钮被剪告警", "isWrite": 1},
            {
                "varName": "button_cut_status",
                "showName": "按钮被剪告警处理状态",
                "isWrite": 1,
            },
            {
                "varName": "status_door_open",
                "showName": "门控制状态",
                "isWrite": 1,
            },
        ]
        vn, err = _resolve_writable_variable_name("D1", "门控制状态")
        assert err is None
        assert vn == "status_door_open"

    @patch("platform_mcp.runtime.tools.device.call_platform_api")
    def test_no_fuzzy_false_positive(self, mock_api):
        """全量列表不应因模糊子串误匹配到错误 varName。"""
        mock_api.side_effect = [
            [],  # showName 筛选无结果
            [
                {
                    "varName": "status_door_control",
                    "showName": "门禁控制状态",
                    "isWrite": 1,
                },
                {
                    "varName": "status_door_open",
                    "showName": "门控制状态",
                    "isWrite": 1,
                },
            ],
        ]
        vn, err = _resolve_writable_variable_name("D1", "门控制状态")
        assert vn == "status_door_open"
        assert err is None


class TestDeviceCmdPreconditions:
    def test_disabled_device(self):
        err = _check_device_cmd_preconditions(
            {"deviceName": "门禁", "enableStatus": 0, "onlineStatus": 1}
        )
        assert err and "停用" in err

    def test_disabled_via_device_status(self):
        err = _check_device_cmd_preconditions(
            {"deviceName": "门禁", "deviceStatus": 0, "onlineStatus": 1}
        )
        assert err and "停用" in err

    def test_offline_device_allowed(self):
        """离线设备不拦截下发，由平台 API 返回结果。"""
        err = _check_device_cmd_preconditions(
            {"deviceName": "门禁", "enableStatus": 1, "onlineStatus": 0}
        )
        assert err is None


class TestVarListRequest:
    def test_var_name_filter(self):
        req = _build_var_list_request("D1", "switch")
        assert req == {"deviceCode": "D1", "varName": "switch"}

    def test_show_name_filter(self):
        req = _build_var_list_request("D1", "门控制状态")
        assert req == {"deviceCode": "D1", "showName": "门控制状态"}


class TestSendCmdPayload:
    def test_vv_string_and_task_no(self):
        payload = _build_send_cmd_payload(
            device_code="D1",
            var_name="switch",
            variable_value=1,
            operate_name="测试",
        )
        assert payload["dn"] == "D1"
        assert payload["vs"] == [{"vn": "switch", "vv": "1"}]
        assert payload["willPostTs"] is True
        assert isinstance(payload.get("taskNo"), str) and payload["taskNo"]


class TestSendDeviceCmd:
    @patch(
        "platform_mcp.runtime.tool_preflight.ensure_tool_args", side_effect=lambda _n, args: args
    )
    @patch("platform_mcp.runtime.tools.device.ask_user_confirm", return_value=True)
    @patch("platform_mcp.runtime.tools.device.call_platform_api")
    def test_send_success(self, mock_api, _confirm, _ensure):
        def _api_side_effect(*, method, path, data=None, **kwargs):
            if path.startswith("/device/getDeviceByCode"):
                return {"deviceCode": "D1", "deviceName": "泵1"}
            if path == "/device/getVarListByCode":
                return [{"varName": "switch", "showName": "开关", "isWrite": 1}]
            if path == "/device/sendCmd":
                return {}
            raise AssertionError(f"unexpected path: {path}")

        mock_api.side_effect = _api_side_effect
        raw = send_device_cmd.invoke(
            {
                "device_code": "D1",
                "variable_name": "switch",
                "variable_value": "1",
            }
        )
        assert '"ok": true' in raw or '"ok":true' in raw.replace(" ", "")
        send_calls = [
            c for c in mock_api.call_args_list if c.kwargs.get("path") == "/device/sendCmd"
        ]
        assert len(send_calls) == 1
        assert send_calls[0].kwargs["data"]["dn"] == "D1"
        assert send_calls[0].kwargs["data"]["vs"][0]["vn"] == "switch"
        assert send_calls[0].kwargs["data"]["vs"][0]["vv"] == "1"
        assert send_calls[0].kwargs["data"]["willPostTs"] is True
        assert send_calls[0].kwargs["data"].get("taskNo")

    @patch(
        "platform_mcp.runtime.tool_preflight.ensure_tool_args", side_effect=lambda _n, args: args
    )
    @patch("platform_mcp.runtime.tools.device.ask_user_confirm", return_value=True)
    @patch("platform_mcp.runtime.tools.device.call_platform_api")
    def test_offline_device_still_sends(self, mock_api, _confirm, _ensure):
        """离线设备允许 confirm 后下发。"""

        def _api_side_effect(*, method, path, data=None, **kwargs):
            if path.startswith("/device/getDeviceByCode"):
                return {
                    "deviceCode": "D1",
                    "deviceName": "离线门禁",
                    "enableStatus": 1,
                    "onlineStatus": 0,
                }
            if path == "/device/getVarListByCode":
                return [{"varName": "switch", "showName": "开关", "isWrite": 1}]
            if path == "/device/sendCmd":
                return {}
            raise AssertionError(f"unexpected path: {path}")

        mock_api.side_effect = _api_side_effect
        raw = send_device_cmd.invoke(
            {
                "device_code": "D1",
                "variable_name": "switch",
                "variable_value": "1",
            }
        )
        assert '"ok": true' in raw or '"ok":true' in raw.replace(" ", "")
        assert mock_api.call_args_list[-1].kwargs.get("path") == "/device/sendCmd"

    @patch(
        "platform_mcp.runtime.tool_preflight.ensure_tool_args", side_effect=lambda _n, args: args
    )
    @patch("platform_mcp.runtime.tools.device.ask_user_confirm", return_value=True)
    @patch("platform_mcp.runtime.tools.device.call_platform_api")
    def test_resolve_show_name_to_var_name(self, mock_api, _confirm, _ensure):
        """中文 showName 应通过服务端筛选解析为 varName。"""

        def _api_side_effect(*, method, path, data=None, **kwargs):
            if path.startswith("/device/getDeviceByCode"):
                return {
                    "deviceCode": "D1",
                    "deviceName": "B口门禁",
                    "enableStatus": 1,
                    "onlineStatus": 1,
                }
            if path == "/device/getVarListByCode":
                if data and data.get("showName") == "门控制状态":
                    return [
                        {
                            "varName": "status_door_open",
                            "showName": "门控制状态",
                            "isWrite": 1,
                        }
                    ]
                return []
            if path == "/device/sendCmd":
                return True
            raise AssertionError(f"unexpected path: {path}")

        mock_api.side_effect = _api_side_effect
        raw = send_device_cmd.invoke(
            {
                "device_code": "D1",
                "variable_name": "门控制状态",
                "variable_value": "1",
            }
        )
        assert '"ok": true' in raw or '"ok":true' in raw.replace(" ", "")
        send_calls = [
            c for c in mock_api.call_args_list if c.kwargs.get("path") == "/device/sendCmd"
        ]
        assert send_calls[0].kwargs["data"]["vs"][0]["vn"] == "status_door_open"

    @patch(
        "platform_mcp.runtime.tool_preflight.ensure_tool_args", side_effect=lambda _n, args: args
    )
    @patch("platform_mcp.runtime.tools.device.ask_user_confirm", return_value=True)
    @patch("platform_mcp.runtime.tools.device.call_platform_api")
    def test_blocked_when_device_disabled(self, mock_api, _confirm, _ensure):
        """设备停用时应在 HITL 前拦截，不调用 sendCmd。"""

        def _api_side_effect(*, method, path, data=None, **kwargs):
            if path.startswith("/device/getDeviceByCode"):
                return {
                    "deviceCode": "D1",
                    "deviceName": "B口门禁",
                    "enableStatus": 0,
                    "onlineStatus": 1,
                }
            if path == "/device/getVarListByCode":
                return [{"varName": "switch", "showName": "开关", "isWrite": 1}]
            raise AssertionError(f"unexpected path: {path}")

        mock_api.side_effect = _api_side_effect
        raw = send_device_cmd.invoke(
            {
                "device_code": "D1",
                "variable_name": "开关",
                "variable_value": "1",
            }
        )
        assert "停用" in raw
        send_calls = [
            c for c in mock_api.call_args_list if c.kwargs.get("path") == "/device/sendCmd"
        ]
        assert len(send_calls) == 0

    @patch(
        "platform_mcp.runtime.tool_preflight.ensure_tool_args", side_effect=lambda _n, args: args
    )
    @patch("platform_mcp.runtime.tools.device.ask_user_confirm", return_value=False)
    @patch("platform_mcp.runtime.tools.device.call_platform_api")
    def test_user_reject(self, mock_api, _confirm, _ensure):
        def _api_side_effect(*, method, path, data=None, **kwargs):
            if path.startswith("/device/getDeviceByCode"):
                return {"deviceCode": "D1", "deviceName": "泵1"}
            if path == "/device/getVarListByCode":
                return [{"varName": "switch", "showName": "开关", "isWrite": 1}]
            raise AssertionError(f"unexpected path: {path}")

        mock_api.side_effect = _api_side_effect
        raw = send_device_cmd.invoke(
            {
                "device_code": "D1",
                "variable_name": "switch",
                "variable_value": "0",
            }
        )
        assert "取消" in raw
        send_calls = [
            c for c in mock_api.call_args_list if c.kwargs.get("path") == "/device/sendCmd"
        ]
        assert len(send_calls) == 0


class TestSendDeviceCmdPlatformError:
    @patch(
        "platform_mcp.runtime.tool_preflight.ensure_tool_args", side_effect=lambda _n, args: args
    )
    @patch("platform_mcp.runtime.tools.device.ask_user_confirm", return_value=True)
    @patch("platform_mcp.runtime.tools.device.call_platform_api")
    def test_platform_error_includes_data(self, mock_api, _confirm, _ensure):
        """平台 sendCmd 失败时应原样透传 data 到 tool_result。"""

        def _api_side_effect(*, method, path, data=None, **kwargs):
            if path.startswith("/device/getDeviceByCode"):
                return {"deviceCode": "D1", "deviceName": "B口门禁", "enableStatus": 1}
            if path == "/device/getVarListByCode":
                return [{"varName": "switch", "showName": "开关", "isWrite": 1}]
            if path == "/device/sendCmd":
                raise PlatformApiError(
                    "发生错误",
                    code=500,
                    data={"reason": "变量不可写", "varName": "switch"},
                )
            raise AssertionError(f"unexpected path: {path}")

        mock_api.side_effect = _api_side_effect
        import json

        raw = send_device_cmd.invoke(
            {
                "device_code": "D1",
                "variable_name": "switch",
                "variable_value": "1",
            }
        )
        body = json.loads(raw)
        assert body["ok"] is False
        assert body["data"]["platform_data"] == {
            "reason": "变量不可写",
            "varName": "switch",
        }
        assert "变量不可写" in body["summary"] or "platform" in str(body["data"])

    @patch(
        "platform_mcp.runtime.tool_preflight.ensure_tool_args", side_effect=lambda _n, args: args
    )
    @patch("platform_mcp.runtime.tools.device.ask_user_confirm", return_value=True)
    @patch("platform_mcp.runtime.tools.device.call_platform_api")
    def test_auto_retry_alternate_variable_for_generic_action(self, mock_api, _confirm, _ensure):
        """非门控动作：首次 varName 失败且存在更优备选时，底层自动换变量重试一次。"""

        send_attempts: list[str] = []

        def _api_side_effect(*, method, path, data=None, **kwargs):
            if path.startswith("/device/getDeviceByCode"):
                return {"deviceCode": "D1", "deviceName": "风机1", "enableStatus": 1}
            if path == "/device/getVarListByCode":
                return [
                    {"varName": "power_status", "showName": "电源状态", "isWrite": 1},
                    {"varName": "switch", "showName": "开关", "isWrite": 1},
                ]
            if path == "/device/sendCmd":
                vn = (data or {}).get("vs", [{}])[0].get("vn", "")
                send_attempts.append(vn)
                if vn == "power_status":
                    raise PlatformApiError("发生错误", code=500, data="变量不可写")
                if vn == "switch":
                    return {}
                raise AssertionError(f"unexpected vn: {vn}")
            raise AssertionError(f"unexpected path: {path}")

        mock_api.side_effect = _api_side_effect
        import json

        raw = send_device_cmd.invoke(
            {
                "device_code": "D1",
                "variable_name": "power_status",
                "variable_value": "1",
                "action": "开启",
            }
        )
        body = json.loads(raw)
        assert body["ok"] is True
        assert send_attempts == ["power_status", "switch"]
        assert body["data"]["auto_retry"]["to"] == "switch"

    @patch(
        "platform_mcp.runtime.tool_preflight.ensure_tool_args", side_effect=lambda _n, args: args
    )
    @patch("platform_mcp.runtime.tools.device.ask_user_confirm", return_value=True)
    @patch("platform_mcp.runtime.tools.device.call_platform_api")
    def test_door_action_no_auto_retry_alternate_variable(self, mock_api, _confirm, _ensure):
        """开门/关门失败时不得换 status_door_open 等备选变量重试。"""

        send_attempts: list[str] = []

        def _api_side_effect(*, method, path, data=None, **kwargs):
            if path.startswith("/device/getDeviceByCode"):
                return {"deviceCode": "D1", "deviceName": "B口门禁", "enableStatus": 1}
            if path == "/device/getVarListByCode":
                return [
                    {
                        "varName": "status_door_control",
                        "showName": "门控制状态",
                        "isWrite": 1,
                    },
                    {
                        "varName": "status_door_open",
                        "showName": "开门状态",
                        "isWrite": 1,
                    },
                ]
            if path == "/device/sendCmd":
                vn = (data or {}).get("vs", [{}])[0].get("vn", "")
                send_attempts.append(vn)
                if vn == "status_door_control":
                    raise PlatformApiError("发生错误", code=500, data="control 下发失败")
                raise AssertionError(f"unexpected vn: {vn}")
            raise AssertionError(f"unexpected path: {path}")

        mock_api.side_effect = _api_side_effect
        import json

        raw = send_device_cmd.invoke(
            {
                "device_code": "D1",
                "variable_name": "status_door_control",
                "variable_value": "1",
                "action": "开门",
            }
        )
        body = json.loads(raw)
        assert body["ok"] is False
        assert send_attempts == ["status_door_control"]
        assert "auto_retry" not in (body.get("data") or {})

    @patch(
        "platform_mcp.runtime.tool_preflight.ensure_tool_args", side_effect=lambda _n, args: args
    )
    @patch("platform_mcp.runtime.tools.device.ask_user_confirm", return_value=True)
    @patch("platform_mcp.runtime.tools.device.call_platform_api")
    def test_door_action_missing_control_var_fails(self, mock_api, _confirm, _ensure):
        """设备无 status_door_control 时开门应硬失败。"""

        def _api_side_effect(*, method, path, data=None, **kwargs):
            if path.startswith("/device/getDeviceByCode"):
                return {"deviceCode": "D1", "deviceName": "空调1", "enableStatus": 1}
            if path == "/device/getVarListByCode":
                return [
                    {"varName": "status_door_open", "showName": "开门状态", "isWrite": 1},
                ]
            raise AssertionError(f"unexpected path: {path}")

        mock_api.side_effect = _api_side_effect
        import json

        raw = send_device_cmd.invoke(
            {
                "device_code": "D1",
                "action": "开门",
            }
        )
        body = json.loads(raw)
        assert body["ok"] is False
        assert "status_door_control" in body["summary"]
        send_calls = [
            c for c in mock_api.call_args_list if c.kwargs.get("path") == "/device/sendCmd"
        ]
        assert send_calls == []

    @patch(
        "platform_mcp.runtime.tool_preflight.ensure_tool_args", side_effect=lambda _n, args: args
    )
    @patch("platform_mcp.runtime.tools.device.ask_user_confirm", return_value=True)
    @patch("platform_mcp.runtime.tools.device.call_platform_api")
    def test_broadcast_play_sends_content(self, mock_api, _confirm, _ensure):
        """播报应向 play 下发正文。"""

        def _api_side_effect(*, method, path, data=None, **kwargs):
            if path.startswith("/device/getDeviceByCode"):
                return {"deviceCode": "B1", "deviceName": "大厅广播", "enableStatus": 1}
            if path == "/device/getVarListByCode":
                return [
                    {"varName": "play", "showName": "播报", "isWrite": 1},
                    {"varName": "volume", "showName": "音量", "isWrite": 1},
                ]
            if path == "/device/sendCmd":
                return {}
            raise AssertionError(f"unexpected path: {path}")

        mock_api.side_effect = _api_side_effect
        import json

        raw = send_device_cmd.invoke(
            {
                "device_code": "B1",
                "action": "播报",
                "variable_value": "请注意安全",
            }
        )
        body = json.loads(raw)
        assert body["ok"] is True
        send_calls = [
            c for c in mock_api.call_args_list if c.kwargs.get("path") == "/device/sendCmd"
        ]
        assert send_calls[0].kwargs["data"]["vs"][0]["vn"] == "play"
        assert send_calls[0].kwargs["data"]["vs"][0]["vv"] == "请注意安全"

    @patch(
        "platform_mcp.runtime.tool_preflight.ensure_tool_args", side_effect=lambda _n, args: args
    )
    @patch("platform_mcp.runtime.tools.device.ask_user_confirm", return_value=True)
    @patch("platform_mcp.runtime.tools.device.call_platform_api")
    def test_broadcast_missing_play_fails(self, mock_api, _confirm, _ensure):
        """设备无 play 时播报应硬失败。"""

        def _api_side_effect(*, method, path, data=None, **kwargs):
            if path.startswith("/device/getDeviceByCode"):
                return {"deviceCode": "D1", "deviceName": "空调1", "enableStatus": 1}
            if path == "/device/getVarListByCode":
                return [{"varName": "switch", "showName": "开关", "isWrite": 1}]
            raise AssertionError(f"unexpected path: {path}")

        mock_api.side_effect = _api_side_effect
        import json

        raw = send_device_cmd.invoke(
            {
                "device_code": "D1",
                "action": "播报",
                "variable_value": "测试",
            }
        )
        body = json.loads(raw)
        assert body["ok"] is False
        assert "play" in body["summary"]

    @patch(
        "platform_mcp.runtime.tool_preflight.ensure_tool_args", side_effect=lambda _n, args: args
    )
    @patch("platform_mcp.runtime.tools.device.ask_user_confirm", return_value=True)
    @patch("platform_mcp.runtime.tools.device.call_platform_api")
    def test_driver_timeout_no_auto_retry(self, mock_api, _confirm, _ensure):
        """驱动超时类错误不应换变量重试。"""

        def _api_side_effect(*, method, path, data=None, **kwargs):
            if path.startswith("/device/getDeviceByCode"):
                return {"deviceCode": "D1", "deviceName": "B口门禁", "enableStatus": 1}
            if path == "/device/getVarListByCode":
                return [
                    {"varName": "status_door_control", "showName": "门控制状态", "isWrite": 1},
                    {"varName": "status_door_open", "showName": "开门状态", "isWrite": 1},
                ]
            if path == "/device/sendCmd":
                raise PlatformApiError(
                    "发生错误",
                    code=500,
                    data="驱动服务:门禁驱动,超时未响应",
                )
            raise AssertionError(f"unexpected path: {path}")

        mock_api.side_effect = _api_side_effect
        import json

        raw = send_device_cmd.invoke(
            {
                "device_code": "D1",
                "variable_name": "status_door_control",
                "variable_value": "1",
            }
        )
        body = json.loads(raw)
        assert body["ok"] is False
        assert body["data"]["failure_kind"] == "driver_timeout"
        assert body["data"]["platform_data"] == "驱动服务:门禁驱动,超时未响应"
        assert "驱动" in body["summary"] or "超时" in body["summary"]
        send_calls = [
            c for c in mock_api.call_args_list if c.kwargs.get("path") == "/device/sendCmd"
        ]
        assert len(send_calls) == 1


class TestOpenDeviceDetail:
    @patch(
        "platform_mcp.runtime.tool_preflight.ensure_tool_args", side_effect=lambda _n, args: args
    )
    def test_navigate_action(self, _ensure):
        raw = open_device_detail.invoke({"device_code": "D1", "device_name": "泵1"})
        assert "equipment_manage" in raw
        assert "deviceCode" in raw
