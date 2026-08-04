"""告警 brief 映射：对齐 getAlarmList 平台字段。"""

from __future__ import annotations

from platform_mcp.runtime.tools.alarm import _map_alarm_brief_item


def test_map_alarm_brief_uses_device_var_name_and_rank() -> None:
    item = {
        "id": "p_alarm|p_alarm_1|235",
        "deviceName": "系统联调0001",
        "deviceCode": "XTLT_BH_0001",
        "deviceVarName": "float_value_01",
        "alarmValue": "8.0788",
        "startTime": "2026-08-04 09:03:11",
        "status": 1,
        "statusName": "待确认",
        "alarmRankId": 2,
        "alarmRankName": "一般",
        "alarmCategoryId": 1,
        "alarmCategoryName": "有效报警",
        "eventName": "[test7]: warning generated.",
        "regionName": None,
        "subSystemName": "门禁安检子系统",
        "confirmPerson": None,
        "confirmTime": None,
        "processPerson": None,
        "processTime": None,
        "handleMethod": None,
    }
    brief = _map_alarm_brief_item(item)
    assert brief["variableName"] == "float_value_01"
    assert brief["deviceVarName"] == "float_value_01"
    assert brief["alarmRankName"] == "一般"
    assert brief["alarmCategoryName"] == "有效报警"
    assert brief["alarmValue"] == "8.0788"
    assert brief["statusName"] == "待确认"
    assert brief["subSystemName"] == "门禁安检子系统"
    # 不应因缺少旧字段 variableName 而丢变量
    assert "variableName" not in item


def test_map_alarm_brief_falls_back_legacy_variable_name() -> None:
    brief = _map_alarm_brief_item(
        {
            "id": "1",
            "variableName": "legacy_var",
            "status": 2,
        }
    )
    assert brief["variableName"] == "legacy_var"
    assert brief["deviceVarName"] == "legacy_var"
    assert brief["statusName"] == "已确认"
