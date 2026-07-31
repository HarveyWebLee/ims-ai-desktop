"""export_catalog 工具 manifest 导出回归"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.export_catalog import parse_ts_tool_catalog


def test_exported_catalog_json_has_full_manifest():
    catalog_path = Path(__file__).resolve().parent.parent / "app" / "tools" / "catalog.json"
    assert catalog_path.exists(), "请先运行 uv run python scripts/export_catalog.py"
    data = json.loads(catalog_path.read_text(encoding="utf-8"))
    assert isinstance(data, list) and len(data) >= 8
    first = data[0]
    assert "parameters" in first
    assert "risk_level" in first
    assert "side" in first


def test_parse_concatenated_description():
    """TS description 多段 '...' + '...' 拼接应完整导出。"""
    from scripts.tool_catalog_parse import parse_tool_object

    block = """
  {
    name: 'navigate_to',
    description:
      '第一段说明；' +
      '第二段说明。',
    parameters: { type: 'object', properties: {}, required: ['path'] },
    side: 'client',
    risk_level: 'low',
    enabled: true,
  },
"""
    item = parse_tool_object(block)
    assert item is not None
    assert "第一段说明" in item["description"]
    assert "第二段说明" in item["description"]


def test_parse_double_quoted_concatenated_description():
    """项目格式化器改用双引号后，参数内拼接字符串仍应完整解析。"""
    from scripts.tool_catalog_parse import parse_tool_object

    block = """
  {
    name: "query_example",
    description: "工具说明",
    parameters: {
      type: "object",
      properties: {
        start_time: {
          type: "string",
          description: "第一段；" + "第二段。",
        },
      },
      required: [],
    },
    side: "server",
    risk_level: "low",
    enabled: true,
  },
"""
    item = parse_tool_object(block)
    assert item is not None
    assert item["parameters"]["properties"]["start_time"]["description"] == "第一段；第二段。"


def _tool_catalog_ts_path() -> Path:
    # tests/ → platform-agent-service → services → repo root
    return Path(__file__).resolve().parents[3] / "packages" / "agent-core" / "tool-catalog.ts"


def test_parse_query_alarms_has_properties_and_hitl():
    ts_path = _tool_catalog_ts_path()
    content = ts_path.read_text(encoding="utf-8")
    parsed = parse_ts_tool_catalog(content)
    qa = next(t for t in parsed if t["name"] == "query_alarms")
    props = qa["parameters"].get("properties") or {}
    assert "start_time" in props
    assert "device_code" in props
    assert "device_name" in props
    assert qa.get("hitl_fields")
    assert qa["hitl_fields"][0]["type"] == "datetime_range"
    hitl_names = [f["name"] for f in qa["hitl_fields"]]
    assert "device_code" in hitl_names
    assert "device_name" in hitl_names
    assert qa.get("preflight", {}).get("alarm_time") is True


def test_parse_device_hitl_constant_and_inline_fields():
    """设备 HITL 常量引用与内联数组都必须进入导出 catalog。"""
    ts_path = _tool_catalog_ts_path()
    parsed = parse_ts_tool_catalog(ts_path.read_text(encoding="utf-8"))

    detail = next(tool for tool in parsed if tool["name"] == "get_device_detail")
    assert [field["name"] for field in detail["hitl_fields"]] == [
        "device_code",
        "device_name",
    ]

    variables = next(tool for tool in parsed if tool["name"] == "query_device_variables")
    assert [field["name"] for field in variables["hitl_fields"]] == [
        "device_code",
        "device_name",
    ]
    assert variables["preflight"] == {
        "one_of": [["device_code"], ["device_name"]],
    }

    command = next(tool for tool in parsed if tool["name"] == "send_device_cmd")
    assert {field["name"] for field in command["hitl_fields"]} >= {
        "device_code",
        "variable_name",
        "variable_value",
    }
    variable_field = next(f for f in command["hitl_fields"] if f["name"] == "variable_name")
    assert variable_field["type"] == "variable_picker"


def test_parse_matches_ts_source():
    ts_path = _tool_catalog_ts_path()
    content = ts_path.read_text(encoding="utf-8")
    parsed = parse_ts_tool_catalog(content)
    names = {t["name"] for t in parsed}
    assert names >= {
        "navigate_to",
        "open_alarm_detail",
        "query_alarms",
        "get_alarm_detail",
        "download_file",
        "batch_confirm_alarms",
        "batch_process_alarms",
        "query_devices",
        "get_device_detail",
        "query_device_variables",
        "send_device_cmd",
        "open_device_detail",
    }
    download = next(tool for tool in parsed if tool["name"] == "download_file")
    resource_enum = download["parameters"]["properties"]["resource"]["enum"]
    assert resource_enum == [
        "alarm_report",
        "sentry_handover",
        "duty_info",
        "duty_manage",
        "acs_record",
    ]
    when = download["preflight"]["when_resource"]
    assert set(when) == {
        "alarm_report",
        "sentry_handover",
        "duty_info",
        "duty_manage",
        "acs_record",
    }
