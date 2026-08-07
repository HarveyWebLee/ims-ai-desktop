"""
Phase C3：工具 invoke 前统一 preflight。

文件职责
--------
在真正调用平台 API / 执行 Client Tool 之前，统一检查参数是否够用：
缺什么就构造 ask_params interrupt，让用户补表单，而不是把半成品请求打到平台导致 500。

在 Agent 流程中的位置
--------------------
工具执行「门口安检」：
  LLM / Plan 给出 tool + args
    → preflight_tool / ensure_tool_args
    → 通过：规范化后的 args 交给 handler
    → 不通过：ask_user_params → McpHitlSignal → hitl_required JSON

如何被调用
----------
- 各平台工具 handler 入口：``ensure_tool_args(tool_name, args)``
- 编排 / 父图工具包装：``preflight_tool`` 判断是否先发 HITL
- 开关：``settings.agent_preflight_enabled`` 为 false 时整段放行

白话解释
--------
像登机前安检：没带身份证（缺时间范围）就拦下来发表格让你填，
填完再进安检一次；还是不行就报错，绝不让你空着手登机（调平台）。

校验层次（由上到下）:
1. catalog preflight 声明（alarm_time / one_of / when_resource）
2. JSON Schema required（navigate_to 等简单工具）
3. platform_api_index 浅层必填（对照真实 HTTP body）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from contracts.alarm_params import (
    QUERY_ALARM_FIELDS,
    build_alarm_list_filter_payload,
    resolve_or_prepare_alarm_times,
    to_platform_time,
)
from contracts.export_infer import (
    EXPORT_ALARM_BATCH_MAX,
    EXPORT_RESOURCE_CONFIRMED_KEY,
    SUPPORTED_EXPORT_RESOURCES,
    TIME_ONLY_EXPORT_RESOURCES,
    export_resource_select_field,
    resolve_export_resource,
)
from contracts.settings import settings

# 告警类工具：复杂 HITL 字段（datetime_range 等），优先于 catalog 泛化推导
_HITL_FIELD_OVERRIDES: dict[str, list[dict[str, Any]]] = {
    "query_alarms": QUERY_ALARM_FIELDS,
    "download_file": QUERY_ALARM_FIELDS,
    "batch_confirm_alarms": QUERY_ALARM_FIELDS,
    "batch_process_alarms": QUERY_ALARM_FIELDS,
    "get_device_detail": [
        {
            "name": "device_code",
            "label": "设备编码",
            "type": "text",
            "required": False,
            "description": "设备唯一编码（与设备名称二选一）",
        },
        {
            "name": "device_name",
            "label": "设备名称",
            "type": "text",
            "required": False,
            "description": "设备名称（与设备编码二选一）",
        },
    ],
    "query_device_variables": [
        {
            "name": "device_code",
            "label": "设备编码",
            "type": "text",
            "required": False,
            "description": "设备唯一编码（与设备名称二选一）",
        },
        {
            "name": "device_name",
            "label": "设备名称",
            "type": "text",
            "required": False,
            "description": "设备名称（与设备编码二选一）",
        },
    ],
    "query_device_variable_realtime": [
        {
            "name": "device_code",
            "label": "设备编码",
            "type": "text",
            "required": False,
        },
        {
            "name": "device_name",
            "label": "设备名称",
            "type": "text",
            "required": False,
        },
        {
            "name": "variable_name",
            "label": "变量名",
            "type": "text",
            "required": False,
            "description": "可选；留空表示查询该设备全部变量实时值",
        },
    ],
    "query_device_variable_history": [
        {
            "name": "device_code",
            "label": "设备编码",
            "type": "text",
            "required": False,
        },
        {
            "name": "device_name",
            "label": "设备名称",
            "type": "text",
            "required": False,
        },
        {
            "name": "variable_name",
            "label": "变量名",
            "type": "text",
            "required": True,
        },
        {
            "name": "time_range",
            "label": "时间范围",
            "type": "datetime_range",
            "required": True,
        },
    ],
    "send_device_cmd": [
        {
            "name": "device_code",
            "label": "目标设备",
            "type": "device_picker",
            "required": True,
            "description": "可通过分组、类型、区域、名称、编码、在线状态筛选后单选",
        },
        {
            "name": "variable_name",
            "label": "目标变量",
            "type": "variable_picker",
            "required": False,
            "writableOnly": False,
            "dependsOn": "device_code",
            "description": "先选设备后，从该设备全部变量中选择",
        },
        {
            "name": "variable_value",
            "label": "写入值",
            "type": "text",
            "required": False,
        },
        {
            "name": "operate_name",
            "label": "操作说明",
            "type": "text",
            "required": False,
        },
    ],
}

# 时间筛选类工具在 preflight 阶段对照 getAlarmList 校验（批量写操作拉列表同源）
_LIST_FETCH_TOOLS = frozenset(
    {"query_alarms", "batch_confirm_alarms", "batch_process_alarms", "get_alarm_detail"}
)


@dataclass
class PreflightResult:
    """
    preflight 结果。

    字段:
        args: 规范化后的参数（如时间字段 enrich 后）
        interrupt: 非空则应暂停并展示 HITL；结构含 type=ask_params、tool、message、fields
    """

    args: dict[str, Any]
    interrupt: dict[str, Any] | None = None


def _has_text(value: Any) -> bool:
    """字符串去空白后是否非空（one_of / 缺参判断公用）。"""
    return bool(str(value or "").strip())


def _ask_params_interrupt(
    *,
    tool: str,
    message: str,
    fields: list[dict[str, Any]],
    current: dict[str, Any],
) -> dict[str, Any]:
    """构造前端可识别的 ask_params interrupt payload（含 current 供表单预填）。"""
    from contracts.hitl import filter_hitl_current

    payload: dict[str, Any] = {
        "type": "ask_params",
        "tool": tool,
        "message": message,
        "fields": fields,
    }
    # 仅下发非空预填，避免空字符串/[""] 把多选 Select 冲成空白已选项
    filled = filter_hitl_current(current)
    if filled:
        payload["current"] = filled
    return payload


def _missing_schema_required(args: dict[str, Any], required: list[str]) -> list[str]:
    """对照 JSON Schema required 检查缺参字段名。"""
    missing: list[str] = []
    for field in required:
        val = args.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            missing.append(field)
    return missing


def _hitl_fields_for_tool(tool_name: str, missing: list[str] | None = None) -> list[dict[str, Any]]:
    """按工具名取 HITL 字段；missing 非空时从 catalog 推导。"""
    from contracts.tool_catalog_loader import hitl_fields_for_missing

    if missing:
        return hitl_fields_for_missing(
            tool_name,
            missing,
            overrides=_HITL_FIELD_OVERRIDES,
        )
    return list(_HITL_FIELD_OVERRIDES.get(tool_name) or [])


def _preflight_catalog_schema(tool_name: str, args: dict[str, Any]) -> PreflightResult | None:
    """
    基于 catalog.json 的 parameters.required 做通用 schema 校验。

    无 required 或未注册工具时返回 None（交给领域 handler 或放行）。
    """
    from contracts.tool_catalog_loader import (
        get_schema_required,
        get_tool_manifest,
        hitl_fields_for_missing,
    )

    manifest = get_tool_manifest(tool_name)
    if not manifest:
        return None

    required = get_schema_required(tool_name)
    if not required:
        return None

    missing = _missing_schema_required(args, required)
    if not missing:
        return PreflightResult(args=dict(args), interrupt=None)

    desc = str(manifest.get("description") or tool_name)[:80]
    fields = hitl_fields_for_missing(
        tool_name,
        missing,
        overrides=_HITL_FIELD_OVERRIDES,
    )
    return PreflightResult(
        args=dict(args),
        interrupt=_ask_params_interrupt(
            tool=tool_name,
            message=f"请补充「{desc}」所需参数",
            fields=fields,
            current=args,
        ),
    )


def _satisfies_one_of(args: dict[str, Any], groups: list[list[str]]) -> bool:
    """catalog one_of：任一组字段全部有值即满足。"""
    for group in groups:
        if not group:
            continue
        if all(_has_text(args.get(field)) for field in group):
            return True
    return False


# 岗哨交接等非告警导出：HITL 仅补时间，不展示告警筛选字段
_EXPORT_TIME_ONLY_FIELDS: list[dict[str, Any]] = [
    field for field in QUERY_ALARM_FIELDS if str(field.get("name") or "") == "time_range"
] or [
    {
        "name": "time_range",
        "label": "时间范围",
        "type": "datetime_range",
        "required": True,
        "description": "选择开始与结束的日期时间（精确到秒）",
    }
]


def _preflight_download_resource(args: dict[str, Any]) -> PreflightResult:
    """
    导出 resource 门控（先于时间 HITL）。

    - 调用方（大模型 / Plan LLM / HITL 确认）已提供合法 resource → 原样放行
    - 空或非法 → ask_params 选业务类型（可用会话上下文仅生成候选列表，不静默写入）
    """
    data = dict(args)
    existing = str(data.get("resource") or "").strip()
    supported = set(SUPPORTED_EXPORT_RESOURCES)

    if data.get(EXPORT_RESOURCE_CONFIRMED_KEY) and existing in supported:
        return PreflightResult(args=data, interrupt=None)

    # 信任模型 / 上游已填的合法 resource，不再用正则或焦点覆盖
    if existing in supported:
        return PreflightResult(args=data, interrupt=None)

    from contracts.context import current_recent_user_messages, current_user_utterance

    utterance = (current_user_utterance.get() or "").strip()
    recent = list(current_recent_user_messages.get() or ())
    decision = resolve_export_resource(utterance, recent_messages=recent)
    candidates = list(decision.candidates) or list(SUPPORTED_EXPORT_RESOURCES)
    cleared = {**data, "resource": ""}
    fields = [export_resource_select_field(candidates), *_EXPORT_TIME_ONLY_FIELDS]
    return PreflightResult(
        args=cleared,
        interrupt=_ask_params_interrupt(
            tool="download_file",
            message="请选择要导出的业务类型与时间范围",
            fields=fields,
            current=cleared,
        ),
    )


def _preflight_alarm_time_tool(
    tool_name: str,
    args: dict[str, Any],
    *,
    message: str,
    fields: list[dict[str, Any]] | None = None,
) -> PreflightResult:
    """query_alarms / download_file / batch_*（无 alarm_ids）时间 preflight。

    仅校验调用方已提供的时间能否解析；不再从用户原话正则回填。
    唯一设备焦点可预填 device_code / device_name，减少「这个设备」再次选设备。
    """
    from contracts.context import current_device_focus
    from contracts.device_focus import merge_unique_device_focus_into_args

    data = merge_unique_device_focus_into_args(dict(args), current_device_focus.get())
    start = str(data.get("start_time") or "")
    end = str(data.get("end_time") or "")
    _, _, needs_hitl = resolve_or_prepare_alarm_times(start, end)
    if needs_hitl:
        hitl_fields = fields if fields is not None else QUERY_ALARM_FIELDS
        current: dict[str, Any] = {
            "start_time": start,
            "end_time": end,
        }
        # 仅告警类表单带 status / 设备槽位回填
        field_names = {str(f.get("name") or "") for f in hitl_fields}
        if "status" in field_names:
            current["status"] = data.get("status", "")
        if "device_code" in field_names and str(data.get("device_code") or "").strip():
            current["device_code"] = str(data.get("device_code")).strip()
        if "device_name" in field_names and str(data.get("device_name") or "").strip():
            current["device_name"] = str(data.get("device_name")).strip()
        return PreflightResult(
            args=dict(data),
            interrupt=_ask_params_interrupt(
                tool=tool_name,
                message=message,
                fields=hitl_fields,
                current=current,
            ),
        )
    return PreflightResult(args=dict(data), interrupt=None)


def _build_platform_preflight_payload(
    tool_name: str,
    args: dict[str, Any],
) -> tuple[str, str, dict[str, Any] | None] | None:
    """
    为 validate_request_fields 构造待校验 payload。

    返回 (path, method, payload)；无法构造时返回 None（不阻断）。

    白话：把「Agent 工具参数」翻译成「平台 HTTP 真实会发的 body」，
    再拿去对照 swagger 索引看缺不缺必填字段。构不出合法 body 时宁可不拦。
    """
    from contracts.tool_catalog_loader import get_tool_platform_api

    name = (tool_name or "").strip()

    # 详情工具实际调 getAlarmList + ids 过滤；用宽时间窗凑齐必填时间字段
    if name == "get_alarm_detail":
        aid = str(args.get("alarm_id") or "").strip()
        if not aid:
            return None
        return (
            "/alarm/getAlarmList",
            "POST",
            {
                "ids": [aid],
                "page": 1,
                "size": 1,
                "startTime": "2000-01-01 00:00:00",
                "endTime": "2099-12-31 23:59:59",
                "deviceCodes": [],
                "variableNames": [],
                "alarmCategoryId": [],
                "alarmRankId": [],
                "status": [],
            },
        )

    if name == "get_device_detail":
        code = str(args.get("device_code") or "").strip()
        if code:
            return f"/device/getDeviceByCode/{code}", "GET", None
        return None

    if name == "query_device_variables":
        code = str(args.get("device_code") or "").strip()
        if not code:
            return None
        from contracts.device_lookup import build_var_list_request

        var_name = str(args.get("var_name") or "").strip()
        payload = build_var_list_request(code, var_name)
        return "/device/getVarListByCode", "POST", payload

    if name == "send_device_cmd":
        code = str(args.get("device_code") or "").strip()
        vn = str(args.get("variable_name") or "").strip()
        vv = args.get("variable_value")
        if not code or not vn or vv is None or str(vv).strip() == "":
            return None
        from contracts.device_lookup import build_send_cmd_payload

        return (
            "/device/sendCmd",
            "POST",
            build_send_cmd_payload(
                device_code=code,
                var_name=vn,
                variable_value=vv,
                operate_name=str(args.get("operate_name") or "AI助手下发指令"),
            ),
        )

    if name == "query_devices":
        status_raw = str(args.get("online_status") or "").strip()
        status_code = None
        if status_raw:
            from contracts.device_lookup import build_device_list_payload, map_online_status_token

            status_code = map_online_status_token(status_raw)

        payload = build_device_list_payload(
            search=str(args.get("search") or ""),
            device_name=str(args.get("device_name") or ""),
            device_code=str(args.get("device_code") or ""),
            online_status=status_code,
        )
        return "/device/getDeviceList", "POST", payload

    # 列表类：时间未解析完或仍需 HITL → 返回 None，交给上层时间 preflight
    if name in _LIST_FETCH_TOOLS - {"get_alarm_detail"}:
        start = str(args.get("start_time") or "")
        end = str(args.get("end_time") or "")
        resolved = resolve_or_prepare_alarm_times(start, end)
        if not resolved or resolved[2]:
            return None
        start_iso, end_iso, _ = resolved
        payload = build_alarm_list_filter_payload(
            start_time=start_iso,
            end_time=end_iso,
            filter_params=args,
            status_fallback=args.get("status") or "",
            alarm_level=args.get("alarm_rank_id") or args.get("alarm_level") or "",
            page=1,
            size=20 if name == "query_alarms" else 1,
        )
        parsed = get_tool_platform_api(name) or ("/alarm/getAlarmList", "POST")
        # 批量写操作最终先拉列表，对照 getAlarmList 而非 confirm/process 接口
        if name in ("batch_confirm_alarms", "batch_process_alarms"):
            return "/alarm/getAlarmList", "POST", payload
        return parsed[0], parsed[1], payload

    # 导出：按 resource 构造平台导出字段校验 payload
    if name == "download_file":
        resource = str(args.get("resource") or "alarm_report").strip()
        start = str(args.get("start_time") or "")
        end = str(args.get("end_time") or "")
        resolved = resolve_or_prepare_alarm_times(start, end)
        if not resolved or resolved[2]:
            return None
        start_iso, end_iso, _ = resolved
        start_fmt = to_platform_time(start_iso)
        end_fmt = to_platform_time(end_iso)

        if resource == "sentry_handover":
            payload: dict[str, Any] = {
                "page": "1",
                "size": "1",
                "startTime": start_fmt,
                "endTime": end_fmt,
            }
            sid = str(args.get("sentry_id") or "").strip()
            if sid:
                payload["sentryId"] = sid
            return "/duty/exportSentryHandover", "GET", payload

        if resource == "duty_info":
            return (
                "/duty/exportDutyInfo",
                "GET",
                {
                    "page": "1",
                    "size": "1",
                    "startTime": start_fmt,
                    "endTime": end_fmt,
                },
            )

        if resource == "duty_manage":
            return (
                "/duty/exportDutyManage",
                "GET",
                {
                    "page": "1",
                    "size": "1",
                    "startTime": start_fmt,
                    "endTime": end_fmt,
                },
            )

        if resource == "acs_record":
            payload = {
                "page": "1",
                "size": "1",
                "startTime": start_fmt,
                "endTime": end_fmt,
            }
            pid = str(args.get("person_id") or "").strip()
            if pid:
                payload["personId"] = pid
            return "/acs/exportAcsRecord", "GET", payload

        if resource != "alarm_report":
            return None

        payload = {
            "page": 1,
            "size": EXPORT_ALARM_BATCH_MAX,
            "startTime": start_fmt,
            "endTime": end_fmt,
        }
        parsed = get_tool_platform_api(name) or ("/alarm/exportAlarm", "GET")
        return parsed[0], parsed[1], payload

    # 其它 Server Tool：有 catalog platform_api 时用原始 args 做最浅校验
    parsed = get_tool_platform_api(name)
    if parsed:
        return parsed[0], parsed[1], dict(args)
    return None


def _preflight_platform_api_payload(tool_name: str, args: dict[str, Any]) -> PreflightResult:
    """
    对照 platform_api_index 做浅层必填校验（catalog 驱动 path 映射）。
    索引缺失时不阻断（validate_request_fields 返回空）。
    """
    from contracts.platform_api_catalog import validate_request_fields

    built = _build_platform_preflight_payload(tool_name, args)
    if not built:
        return PreflightResult(args=dict(args), interrupt=None)

    path, method, payload = built
    if payload is None:
        missing: list[str] = []
    else:
        missing = validate_request_fields(path, payload, method)
    if not missing:
        return PreflightResult(args=dict(args), interrupt=None)

    fields = _hitl_fields_for_tool(tool_name)
    return PreflightResult(
        args=dict(args),
        interrupt=_ask_params_interrupt(
            tool=tool_name,
            message=f"缺少平台接口必填参数：{', '.join(missing)}，请补充后重试。",
            fields=fields,
            current=args,
        ),
    )


def _preflight_catalog_rules(tool_name: str, args: dict[str, Any]) -> PreflightResult | None:
    """
    读取 catalog preflight 声明执行领域校验（alarm_time / one_of / when_resource）。

    返回:
        - None：无声明，交给后续 schema / 放行路径
        - PreflightResult(interrupt=None)：已满足（如有 alarm_ids），可直接用
        - PreflightResult(interrupt=...)：需要时间范围 HITL
    """
    from contracts.tool_catalog_loader import get_preflight_config

    cfg = get_preflight_config(tool_name)
    if not cfg:
        return None

    data = dict(args)
    one_of_raw = cfg.get("one_of")
    one_of_groups: list[list[str]] = []
    if isinstance(one_of_raw, list):
        for group in one_of_raw:
            if not isinstance(group, list):
                continue
            fields = [str(field) for field in group if str(field).strip()]
            if fields:
                one_of_groups.append(fields)
    one_of_satisfied = bool(one_of_groups) and _satisfies_one_of(data, one_of_groups)
    if one_of_satisfied:
        # 业务规则：one_of 已满足且含 alarm_ids → 走「指定编号」分支，跳过时间 HITL
        if _has_text(data.get("alarm_ids")):
            return PreflightResult(args=data, interrupt=None)

    # 仅声明 one_of 的工具：任一组满足即放行，否则统一触发补参。
    if not cfg.get("alarm_time"):
        if not one_of_groups:
            return None
        if one_of_satisfied:
            return PreflightResult(args=data, interrupt=None)
        missing = list(dict.fromkeys(field for group in one_of_groups for field in group))
        fields = _hitl_fields_for_tool(tool_name, missing)
        alternatives = "；".join(" + ".join(group) for group in one_of_groups)
        return PreflightResult(
            args=data,
            interrupt=_ask_params_interrupt(
                tool=tool_name,
                message=f"请至少补充一组参数：{alternatives}",
                fields=fields,
                current=data,
            ),
        )

    # download_file：仅当 resource 命中 when_resource（字符串或列表）才做时间校验
    when_resource = cfg.get("when_resource")
    if when_resource:
        resource = str(data.get("resource") or "").strip()
        allowed = (
            [str(x).strip() for x in when_resource]
            if isinstance(when_resource, (list, tuple))
            else [str(when_resource).strip()]
        )
        if resource not in allowed:
            return PreflightResult(args=data, interrupt=None)

    # 再次短路：有 alarm_ids 时不做时间范围询问
    if one_of_groups and _has_text(data.get("alarm_ids")):
        return PreflightResult(args=data, interrupt=None)

    resource = str(data.get("resource") or "").strip()
    download_messages = {
        "sentry_handover": "请选择要导出的岗哨交接时间范围",
        "duty_info": "请选择要导出的值班信息时间范围",
        "duty_manage": "请选择要导出的值班管理时间范围",
        "acs_record": "请选择要导出的出入信息时间范围",
    }
    messages = {
        "query_alarms": "请选择要查询的告警时间范围与筛选条件",
        "download_file": (
            download_messages.get(resource)
            if tool_name == "download_file" and resource in download_messages
            else "请选择要导出的告警时间范围与筛选条件"
        ),
        "batch_confirm_alarms": "请选择要批量确认的告警时间范围，或提供告警编号列表",
        "batch_process_alarms": "请选择要批量处理的告警时间范围，或提供告警编号列表",
    }
    message = messages.get(tool_name, "请补充时间范围或筛选条件")
    hitl_fields = (
        _EXPORT_TIME_ONLY_FIELDS
        if tool_name == "download_file" and resource in TIME_ONLY_EXPORT_RESOURCES
        else None
    )
    result = _preflight_alarm_time_tool(tool_name, data, message=message, fields=hitl_fields)
    if result.interrupt:
        return result
    return PreflightResult(args=result.args, interrupt=None)


def _preflight_send_device_cmd(args: dict[str, Any]) -> PreflightResult:
    """
    send_device_cmd 领域 preflight：invoke 前走 device_command_resolver。

    缺设备/变量/播报正文时直接 ask_params，避免先调平台再失败；
    硬失败（如无 play）不在此拦截，交给工具返回 non_retryable。

    设备/动作等槽位以工具入参为准（由大模型填写）；缺参走 ask_params。
    本轮原话仅作 user_text 辅助动作/写入值推断。
    多台列表焦点：ask_params 的 device_picker 可带上次筛选（如在线）。
    """
    from contracts.context import current_device_focus, current_user_utterance
    from contracts.device_command_resolver import resolve_device_command
    from contracts.device_focus import apply_device_focus_to_interrupt

    data = dict(args)
    utterance = (current_user_utterance.get() or "").strip()
    user_text = utterance or str(data.get("action") or data.get("variable_name") or "")
    resolution = resolve_device_command(
        device_code=str(data.get("device_code") or ""),
        device_name=str(data.get("device_name") or ""),
        variable_name=str(data.get("variable_name") or ""),
        variable_value=str(data.get("variable_value") or ""),
        action=str(data.get("action") or ""),
        operate_name=str(data.get("operate_name") or ""),
        user_text=user_text,
    )
    merged = {**data, **resolution.to_tool_args()}

    if resolution.is_complete():
        return PreflightResult(args=merged, interrupt=None)

    interrupt = resolution.interrupt
    if not interrupt or interrupt.get("type") != "ask_params":
        return PreflightResult(args=merged, interrupt=None)

    focus = current_device_focus.get()
    interrupt = (
        apply_device_focus_to_interrupt(
            interrupt if isinstance(interrupt, dict) else None,
            focus,
        )
        or interrupt
    )

    fields = list(interrupt.get("fields") or [])
    if not fields:
        return PreflightResult(args=merged, interrupt=None)

    return PreflightResult(
        args=merged,
        interrupt=_ask_params_interrupt(
            tool="send_device_cmd",
            message=str(interrupt.get("message") or "请补充设备指令参数"),
            fields=fields,
            current=merged,
        ),
    )


def preflight_tool(tool_name: str, args: dict[str, Any] | None) -> PreflightResult:
    """
    统一 invoke 前校验（主入口，不主动 interrupt，只返回「要不要问用户」）。

    参数:
        tool_name: 工具名
        args: LLM / Plan 传入的参数

    返回:
        PreflightResult；interrupt 非空表示应暂停并展示 HITL 表单

    分支总览（给小白）:
        开关关 → 原样放行
        有 catalog preflight → 走时间/one_of，再酌情对照平台必填
        get_alarm_detail → schema + 平台
        其它 → 仅 schema.required；都没有则直接放行
        （不在此用正则改写空槽；补参由大模型 / HITL 完成）
    """
    if not settings.agent_preflight_enabled:
        return PreflightResult(args=dict(args or {}), interrupt=None)

    name = (tool_name or "").strip()
    # 字符串参数统一 strip，避免「  空白 」骗过非空检查
    data = {k: (v.strip() if isinstance(v, str) else v) for k, v in dict(args or {}).items()}

    # 空槽补参交给大模型（及 HITL）；不再用正则/会话弱推断改写执行参数

    # ── 导出：先按会话上下文裁决 resource，歧义则 HITL 选择（全会话上下文，非导出专用通道）──
    if name == "download_file":
        resource_gate = _preflight_download_resource(data)
        if resource_gate.interrupt:
            return resource_gate
        data = resource_gate.args

    # ── 路径 1：catalog 声明式 preflight（alarm_time / one_of）──
    catalog_rules = _preflight_catalog_rules(name, data)
    if catalog_rules is not None:
        if catalog_rules.interrupt:
            return catalog_rules
        data = catalog_rules.args
        # 业务规则：批量写操作若用户已给 alarm_ids，不必再凑时间去查列表
        if _has_text(data.get("alarm_ids")) and name in (
            "batch_confirm_alarms",
            "batch_process_alarms",
        ):
            return PreflightResult(args=data, interrupt=None)
        # 业务规则：时间类列表/导出再对照 platform_api_index 浅层必填
        if name in _LIST_FETCH_TOOLS or name == "download_file":
            platform = _preflight_platform_api_payload(name, data)
            if platform.interrupt:
                return platform
            data = platform.args
        return PreflightResult(args=data, interrupt=None)

    # ── 路径 2：设备指令（Resolver 渐进补参，避免无参直调平台）──
    if name == "send_device_cmd":
        return _preflight_send_device_cmd(data)

    # ── 路径 3：告警详情（必有 alarm_id，再构造 getAlarmList 探针 payload）──
    if name == "get_alarm_detail":
        schema = _preflight_catalog_schema(name, data)
        if schema and schema.interrupt:
            return schema
        data = (schema.args if schema else data) or data
        return _preflight_platform_api_payload(name, data)

    # ── 路径 4：简单 required 工具（navigate_to / open_alarm_detail 等）──
    catalog_result = _preflight_catalog_schema(name, data)
    if catalog_result is not None:
        return catalog_result

    return PreflightResult(args=data, interrupt=None)


def ensure_tool_args(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """
    工具内统一入口：preflight + HITL 补参。

    缺参时 ``ask_user_params`` 抛 ``McpHitlSignal`` → MCP 返回 hitl_required；
    Agent 图 interrupt 后带补参重调，本函数再走 preflight 时参数应已齐全。
    """
    result = preflight_tool(tool_name, args)
    if not result.interrupt:
        return result.args

    from contracts.hitl import ask_user_params

    # 优先用 interrupt 已过滤的 current；否则用 args（ask_user_params 内仍会再滤空）
    interrupt_current = result.interrupt.get("current")
    current_for_hitl = (
        dict(interrupt_current) if isinstance(interrupt_current, dict) else dict(result.args)
    )

    # 缺参：抛 McpHitlSignal（不会返回）
    merged = ask_user_params(
        tool=tool_name,
        message=str(result.interrupt.get("message") or "需要补充参数"),
        fields=list(result.interrupt.get("fields") or []),
        current=current_for_hitl,
    )
    combined = {**result.args, **merged}
    # 用户回来后必须再跑一遍 preflight，防止只填了一半就进 handler
    second = preflight_tool(tool_name, combined)
    if second.interrupt:
        raise ValueError(str(second.interrupt.get("message") or "参数仍不完整，请重新选择。"))
    return {**second.args, **merged}
