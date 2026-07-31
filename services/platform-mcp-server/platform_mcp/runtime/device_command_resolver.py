"""
设备指令槽位消解器（Device Command Resolver）。

文件职责
--------
把 LLM / 用户填表得到的口语槽位（device_name、action、variable_name 等）
解析成可下发的三要素：``device_code`` + ``varName`` + ``variable_value``。
能唯一确定则自动补齐；不确定则生成**渐进式** HITL（只问还缺的槽位）。

在 Agent 流程中的位置
--------------------
    send_device_cmd preflight / 工具入参不全
      → resolve_device_command(...)
      → 完整：to_tool_args() 交给平台下发
      → interrupt 非空：ask_params HITL（选设备 / 选变量 / 补写入值）
    下发失败重试：pick_alternate_writable_variable 换备选变量

如何被调用
----------
- 主要：``app.tools`` 设备指令相关路径、tool_preflight
- 依赖：``device_action_catalog``（动作提示）、``platform.device`` API 封装

策略（产品确认）
--------------
- 多台设备：Top1 分数明显高于次选时自动选中，否则下拉消歧
- 多可写变量：同理按动作目录打分；防「开门」误命中 fire_alarm
- 开门/关门：硬绑定 requiredVarName=status_door_control；开门=1、关门=0；
  设备无该变量则硬失败（不 HITL 选其它变量、不 auto_retry；不校验 isWrite）
- 播报：硬绑定 requiredVarName=play；写入值为播报正文（须使用者明确，缺则 HITL）；
  设备无 play 则硬失败（不校验 isWrite）
- 设备离线：不拦截，允许 confirm 后下发；平台异常时返回错误摘要
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from platform_mcp.runtime.device_action_catalog import (
    action_requires_user_value,
    extract_user_value_from_text,
    find_device_action_hint,
    infer_value_from_action,
)
from platform_mcp.runtime.platform_client import PlatformApiError, call_platform_api
from platform_mcp.runtime.tools.device import (
    _fetch_device_variable_records,
    _normalize_name_token,
    _resolve_device_code,
    _resolve_writable_variable_name,
    build_device_list_payload,
)

# Top1 自动选中：与次选分差 ≥ 此值且 Top1 ≥ MIN 时自动采用
_DEVICE_TOP1_SCORE_GAP = 15.0
_DEVICE_TOP1_MIN_SCORE = 70.0
_VARIABLE_TOP1_SCORE_GAP = 12.0
_VARIABLE_TOP1_MIN_SCORE = 65.0

# 门控硬失败哨兵：interrupt.fields 为空，send_device_cmd 直接 ToolResult 失败
_REQUIRED_VAR_UNSUPPORTED_PREFIX = "__REQUIRED_VAR_UNSUPPORTED__:"

MissingSlot = Literal["device", "variable", "value"]


@dataclass
class CommandResolution:
    """
    指令消解结果（一站式返回自动解析字段 + 缺失槽位 + HITL 载荷）。

    字段要点
    --------
    missing : 仍缺的槽位名列表（device / variable / value）
    interrupt : 非空时前端应弹 ask_params，不要直接下发
    auto_resolved : 本轮自动补齐的槽位名，便于审计/调试
    """

    device_code: str | None = None
    device_name: str | None = None
    device_record: dict[str, Any] | None = None
    variable_name: str | None = None
    variable_input: str | None = None
    variable_value: str | None = None
    operate_name: str | None = None
    action: str | None = None
    missing: list[MissingSlot] = field(default_factory=list)
    interrupt: dict[str, Any] | None = None
    auto_resolved: list[str] = field(default_factory=list)

    def is_complete(self) -> bool:
        """是否已具备下发三要素。"""
        return bool(
            self.device_code
            and self.variable_name
            and self.variable_value is not None
            and str(self.variable_value).strip() != ""
        )

    def to_tool_args(self) -> dict[str, Any]:
        """转为 send_device_cmd 参数字典。"""
        out: dict[str, Any] = {}
        if self.device_code:
            out["device_code"] = self.device_code
        if self.device_name:
            out["device_name"] = self.device_name
        if self.variable_input:
            out["variable_name"] = self.variable_input
        elif self.variable_name:
            out["variable_name"] = self.variable_name
        if self.variable_value is not None:
            out["variable_value"] = self.variable_value
        if self.operate_name:
            out["operate_name"] = self.operate_name
        if self.action:
            out["action"] = self.action
        return out


def _score_device_match(query: str, item: dict[str, Any]) -> float:
    """设备名称/编码与查询词的匹配分数（越高越可信）。"""
    q = _normalize_name_token(query)
    if not q:
        return 0.0
    name = str(item.get("deviceName") or "").strip()
    code = str(item.get("deviceCode") or "").strip()
    name_norm = _normalize_name_token(name)
    code_norm = _normalize_name_token(code)

    if name == query or code == query:
        return 100.0
    if name_norm == q or code_norm == q:
        return 95.0
    if q in name_norm:
        ratio = len(q) / max(len(name_norm), 1)
        return 80.0 + min(15.0, ratio * 15.0)
    if name_norm and name_norm in q:
        return 72.0
    if q in code_norm:
        return 68.0
    return 40.0


def _pick_device_by_score(
    query: str,
    records: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], bool]:
    """
    对候选设备打分排序。

    返回 (auto_selected_or_none, sorted_records, auto_selected_flag)。
    """
    if not records:
        return None, [], False
    if len(records) == 1:
        return records[0], records, True

    scored = sorted(
        ((_score_device_match(query, item), item) for item in records),
        key=lambda x: x[0],
        reverse=True,
    )
    sorted_records = [item for _, item in scored]
    top_score, top_item = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else 0.0

    # Top1 够高且与次选拉开差距 → 自动选；否则留给 HITL
    if top_score >= _DEVICE_TOP1_MIN_SCORE and (top_score - second_score) >= _DEVICE_TOP1_SCORE_GAP:
        return top_item, sorted_records, True
    return None, sorted_records, False


def _resolve_device_with_auto_select(
    *,
    device_code: str = "",
    device_name: str = "",
    search: str = "",
) -> tuple[str | None, dict[str, Any] | None, str | None, bool]:
    """
    消解设备编码；多台时 Top1 分数明显领先则自动选中。

    返回 (code, record, error, was_auto_selected)。
    """
    code = (device_code or "").strip()
    name = (device_name or "").strip()
    keyword = (search or name or "").strip()

    # 已有编码：直查平台，不做模糊打分（也不算 auto_selected）
    if code:
        resolved_code, record, err = _resolve_device_code(device_code=code)
        return resolved_code, record, err, False

    if not name and not keyword:
        return None, None, None, False

    query = name or keyword
    payload = build_device_list_payload(
        search=keyword if not name else "",
        device_name=name,
        size=10,
    )
    try:
        data = call_platform_api(
            method="post",
            path="/device/getDeviceList",
            data=payload,
        )
    except PlatformApiError as exc:
        return None, None, str(exc), False

    from platform_mcp.runtime.tools.device import _extract_device_records

    _, records = _extract_device_records(data)
    if not records:
        return None, None, f"未找到与「{query}」匹配的设备。", False

    picked, sorted_records, auto = _pick_device_by_score(query, records)
    if picked is not None and auto:
        dc = str(picked.get("deviceCode") or "")
        if dc:
            return dc, picked, None, True

    if len(sorted_records) == 1:
        item = sorted_records[0]
        return str(item.get("deviceCode") or ""), item, None, True

    # 多台且无法自动选中：返回特殊 error 供上层构建 HITL
    return None, None, f"__MULTIPLE_DEVICES__:{len(sorted_records)}", False


def _score_variable_match(keyword: str, item: dict[str, Any]) -> float:
    """变量 showName/varName 与动作提示词的匹配分数。"""
    kw = _normalize_name_token(keyword)
    if not kw:
        return 0.0
    vn = str(item.get("varName") or item.get("var_name") or "").strip()
    sn = str(item.get("showName") or item.get("show_name") or "").strip()
    vn_norm = _normalize_name_token(vn)
    sn_norm = _normalize_name_token(sn)
    kw_lower = kw.lower()

    if vn == keyword or sn == keyword:
        return 100.0
    if vn_norm == kw or sn_norm == kw:
        return 95.0
    if kw in sn_norm or kw_lower in vn_norm.lower():
        return 85.0 + min(10.0, len(kw) / max(len(sn_norm or vn_norm), 1) * 10.0)
    if sn_norm and kw in sn:
        return 80.0
    if vn_norm and kw_lower in vn_norm.lower():
        return 75.0
    # 硬否决：门控口语不要落到火警/烟雾等告警类变量名上
    if any(k in vn_norm.lower() for k in ("fire", "alarm", "smoke", "fault")):
        if any(k in kw for k in ("门", "开", "关", "door", "open", "close")):
            return 0.0
    return 0.0


def _score_variable_for_action(item: dict[str, Any], action_hint: dict[str, Any]) -> float:
    """结合动作目录 variableHints 对单条可写变量打分。"""
    hints = action_hint.get("variableHints") or []
    best = 0.0
    for hint in hints:
        h = str(hint or "").strip()
        if h:
            best = max(best, _score_variable_match(h, item))
    action_name = str(action_hint.get("action") or "")
    if action_name:
        best = max(best, _score_variable_match(action_name, item))
    return best


def _required_var_meta_for_action(action: str) -> tuple[str | None, str]:
    """
    若动作目录声明 requiredVarName，返回 (varName, 中文标签)。

    标签用于失败提示；缺省时回退为 varName。
    """
    hint = find_device_action_hint(action)
    if not hint:
        return None, ""
    required = str(hint.get("requiredVarName") or "").strip()
    if not required:
        return None, ""
    label = str(hint.get("requiredVarLabel") or "").strip() or required
    return required, label


def _required_var_name_for_action(action: str) -> str | None:
    """若动作目录声明 requiredVarName，返回硬绑定 varName。"""
    required, _ = _required_var_meta_for_action(action)
    return required


def _resolve_required_variable(
    device_code: str,
    required_var: str,
    *,
    var_label: str = "",
) -> tuple[str | None, str | None, str | None]:
    """
    精确查找设备上的硬绑定变量。

    返回 (var_name, display_name, error)；变量不存在时 error 带哨兵前缀。
    不校验 isWrite：存在即允许下发。
    """
    label = (var_label or required_var).strip() or required_var
    try:
        records = _fetch_device_variable_records(device_code)
    except PlatformApiError as exc:
        return None, None, str(exc)

    target: dict[str, Any] | None = None
    for item in records:
        if _var_name_of(item) == required_var:
            target = item
            break

    if target is None:
        if required_var == "play":
            msg = f"该设备未配置变量 {required_var}（{label}），可能不是广播设备或不支持远程播报。"
        elif required_var == "status_door_control":
            msg = f"该设备未配置变量 {required_var}（{label}），可能不是门设备或不支持远程开关门。"
        else:
            msg = f"该设备未配置变量 {required_var}（{label}），可能不支持该控制能力。"
        return None, None, f"{_REQUIRED_VAR_UNSUPPORTED_PREFIX}{msg}"

    sn = _show_name_of(target) or required_var
    return required_var, sn, None


def _pick_variable_by_action_score(
    candidates: list[dict[str, Any]],
    action_hint: dict[str, Any],
) -> tuple[dict[str, Any] | None, bool]:
    """
    对设备变量按动作提示打分；Top1 明显领先则自动选中。

    返回 (picked_item, auto_selected)。
    """
    if not candidates:
        return None, False
    if len(candidates) == 1:
        return candidates[0], True

    scored = sorted(
        ((_score_variable_for_action(item, action_hint), item) for item in candidates),
        key=lambda x: x[0],
        reverse=True,
    )
    top_score, top_item = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else 0.0
    if (
        top_score >= _VARIABLE_TOP1_MIN_SCORE
        and (top_score - second_score) >= _VARIABLE_TOP1_SCORE_GAP
    ):
        return top_item, True
    return None, False


def _var_name_of(item: dict[str, Any]) -> str:
    return str(item.get("varName") or item.get("var_name") or "").strip()


def _show_name_of(item: dict[str, Any]) -> str:
    return str(item.get("showName") or item.get("show_name") or "").strip()


def _resolve_variable_from_hints(
    device_code: str,
    *,
    variable_name: str = "",
    action: str = "",
) -> tuple[str | None, str | None, str | None]:
    """
    解析变量 varName。

    返回 (var_name, variable_input_for_display, error)。
    若 action 声明 requiredVarName（如开门/关门 → status_door_control，播报 → play），
    忽略其它 variable_name，仅精确匹配该变量（不校验 isWrite）。
    """
    action_token = (action or "").strip()
    required, var_label = (
        _required_var_meta_for_action(action_token) if action_token else (None, "")
    )
    if required:
        return _resolve_required_variable(device_code, required, var_label=var_label)

    token = (variable_name or "").strip()
    if token:
        # 显式名仍走 showName→varName 映射；未命中时 _resolve_writable_variable_name
        # 会回退为原 token（HITL 下拉已是 varName，不因未收录而失败）
        vn, err = _resolve_writable_variable_name(device_code, token)
        if err:
            return None, token, err
        return vn, token, None

    action_hint = find_device_action_hint(action)
    if action_hint:
        try:
            records = _fetch_device_variable_records(device_code)
        except PlatformApiError as exc:
            return None, None, str(exc)
        # 不按 isWrite 过滤：动作消解可命中任意已存在变量
        candidates = [r for r in records if _var_name_of(r)]
        picked, auto = _pick_variable_by_action_score(candidates, action_hint)
        if picked is not None and auto:
            vn = _var_name_of(picked)
            sn = _show_name_of(picked) or vn
            if vn:
                return vn, sn, None

    if not action_hint:
        return None, None, None

    # 预拉变量列表：多变量时不允许 hint 模糊检索短路（避免 open 等误命中 fire_alarm）
    try:
        records = _fetch_device_variable_records(device_code)
    except PlatformApiError as exc:
        return None, None, str(exc)
    candidates = [r for r in records if _var_name_of(r)]

    hints = action_hint.get("variableHints") or []
    last_err: str | None = None
    for hint in hints:
        h = str(hint or "").strip()
        if not h:
            continue
        if len(candidates) > 1:
            # 多变量时仅当 hint 对某变量打分明显领先才自动选中
            scored = sorted(
                ((_score_variable_match(h, r), r) for r in candidates),
                key=lambda x: -x[0],
            )
            if scored and scored[0][0] > 0:
                top_score = scored[0][0]
                second = scored[1][0] if len(scored) > 1 else 0.0
                if top_score - second >= 15.0:
                    picked = scored[0][1]
                    vn = _var_name_of(picked)
                    sn = _show_name_of(picked) or vn
                    if vn:
                        return vn, sn, None
            continue
        vn, err = _resolve_writable_variable_name(device_code, h)
        if vn:
            return vn, h, None
        last_err = err

    # 动作提示均未唯一命中：拉变量列表供消歧
    if not candidates:
        try:
            records = _fetch_device_variable_records(device_code)
            candidates = [r for r in records if _var_name_of(r)]
        except PlatformApiError as exc:
            return None, None, str(exc)
    if len(candidates) == 1:
        vn = str(candidates[0].get("varName") or candidates[0].get("var_name") or "").strip()
        sn = str(candidates[0].get("showName") or candidates[0].get("show_name") or vn)
        if vn:
            return vn, sn, None

    if len(candidates) > 1:
        return None, None, f"__MULTIPLE_VARIABLES__:{len(candidates)}"

    return None, None, last_err or "未能从动作推断目标变量，请指定变量名。"


def _build_device_picker_field(*, required: bool = True) -> dict[str, Any]:
    """构造设备单选表格 HITL 字段（前端 device_picker）。"""
    return {
        "name": "device_code",
        "label": "目标设备",
        "type": "device_picker",
        "required": required,
        "description": "可通过分组、类型、区域、名称、编码、在线状态筛选后单选",
    }


def _build_variable_picker_field(
    *,
    required: bool = False,
    device_code: str = "",
) -> dict[str, Any]:
    """构造设备变量下拉 HITL 字段（前端按 device_code 拉取全部变量）。"""
    field: dict[str, Any] = {
        "name": "variable_name",
        "label": "目标变量",
        "type": "variable_picker",
        "required": required,
        "writableOnly": False,
        "dependsOn": "device_code",
        "description": "先选设备后，从该设备全部变量中选择；支持搜索变量名",
    }
    code = (device_code or "").strip()
    if code:
        field["deviceCode"] = code
    return field


def _build_device_select_interrupt(
    *,
    query: str,
    records: list[dict[str, Any]],
    partial: dict[str, Any],
) -> dict[str, Any]:
    """多台设备无法自动选中时的 HITL：设备筛选表格单选。"""
    _ = records  # 候选由前端按筛选条件实时查询，不再塞入有限 options
    fields: list[dict[str, Any]] = [_build_device_picker_field(required=True)]
    if not partial.get("variable_name") and not partial.get("action"):
        fields.append(_build_variable_picker_field(required=False))
        if not str(partial.get("variable_value") or "").strip():
            fields.append(
                {
                    "name": "variable_value",
                    "label": "写入值",
                    "type": "text",
                    "required": False,
                    "description": "选变量后填写要下发的值（播报则为正文）",
                }
            )
    query_label = (query or "").strip() or "目标"
    return {
        "type": "ask_params",
        "tool": "send_device_cmd",
        "message": f"找到多台与「{query_label}」匹配的设备，请在下方表格中筛选并单选目标设备：",
        "fields": fields,
    }


def _build_variable_select_interrupt(
    *,
    device_code: str,
    device_name: str,
    partial: dict[str, Any],
) -> dict[str, Any] | None:
    """多变量时的 HITL：前端按设备拉取全部变量下拉。"""
    try:
        records = _fetch_device_variable_records(device_code)
    except PlatformApiError:
        return None

    named = [r for r in records if (r.get("varName") or r.get("showName"))]
    if len(named) <= 1:
        return None

    display = device_name or device_code
    fields: list[dict[str, Any]] = [
        _build_variable_picker_field(required=True, device_code=device_code),
    ]
    if not str(partial.get("variable_value") or "").strip():
        fields.append(
            {
                "name": "variable_value",
                "label": "写入值",
                "type": "text",
                "required": True,
                "description": "要下发给变量的值",
            }
        )
    return {
        "type": "ask_params",
        "tool": "send_device_cmd",
        "message": f"设备「{display}」存在多个变量，请选择要操作的变量：",
        "fields": fields,
    }


def _build_missing_fields_interrupt(
    missing: list[MissingSlot],
    partial: dict[str, Any],
) -> dict[str, Any]:
    """按缺失槽位生成渐进式 HITL 表单。"""
    fields: list[dict[str, Any]] = []
    messages: list[str] = []

    if "device" in missing:
        messages.append("目标设备")
        fields.append(_build_device_picker_field(required=True))
        action_token = str(partial.get("action") or "").strip()
        # 开门/播报等动作已明确时无需再填变量槽位
        if not action_token and not partial.get("variable_name"):
            messages.append("控制变量")
            fields.append(_build_variable_picker_field(required=False))
            if not str(partial.get("variable_value") or "").strip():
                fields.append(
                    {
                        "name": "variable_value",
                        "label": "写入值",
                        "type": "text",
                        "required": False,
                        "description": "选变量后填写要下发的值（播报则为正文）",
                    }
                )

    if "variable" in missing:
        # 与设备同屏时已追加 variable_picker，避免重复字段
        if not any(f.get("name") == "variable_name" for f in fields):
            messages.append("控制变量")
            device_code = str(partial.get("device_code") or "").strip()
            fields.append(
                _build_variable_picker_field(
                    required=True,
                    device_code=device_code,
                )
            )

    if "value" in missing:
        # 与设备同屏时可能已追加可选写入值，避免重复
        if not any(f.get("name") == "variable_value" for f in fields):
            action_token = str(partial.get("action") or "").strip()
            if action_requires_user_value(action_token):
                messages.append("播报内容")
                fields.append(
                    {
                        "name": "variable_value",
                        "label": "播报内容",
                        "type": "text",
                        "required": True,
                        "description": "请输入要播报的文字内容",
                    }
                )
            else:
                messages.append("写入值")
                fields.append(
                    {
                        "name": "variable_value",
                        "label": "写入值",
                        "type": "text",
                        "required": True,
                        "description": "要下发给变量的值",
                    }
                )

    scope = "、".join(messages) if messages else "参数"
    message = f"请补充设备指令所需的{scope}："
    if "device" in missing:
        action_token = str(partial.get("action") or "").strip()
        required = _required_var_name_for_action(action_token) if action_token else None
        if required == "status_door_control":
            message = "未指定门禁设备，请在下方表格中筛选并单选要开关门的设备："
        elif required == "play":
            message = "未指定广播设备，请在下方表格中筛选并单选要播报的设备："
        elif not action_token and not str(partial.get("variable_name") or "").strip():
            message = (
                "未指定设备与控制内容，请选择目标设备，并从该设备变量中选择要下发的变量"
                "（支持任意具备变量的设备，不限于门禁或广播）："
            )
        elif missing == ["device"] or set(missing) <= {"device", "value"}:
            message = "未指定设备，请在下方表格中筛选并单选目标设备："

    return {
        "type": "ask_params",
        "tool": "send_device_cmd",
        "message": message,
        "fields": fields,
    }


def resolve_device_command(
    *,
    device_code: str = "",
    device_name: str = "",
    variable_name: str = "",
    variable_value: str = "",
    action: str = "",
    operate_name: str = "",
    user_text: str = "",
) -> CommandResolution:
    """
    设备指令槽位一站式消解。

    参数:
        user_text: 用户原话（辅助 action→value 推断，可选）

    返回:
        CommandResolution；interrupt 非空表示需 HITL 补参/消歧
    """
    res = CommandResolution(
        operate_name=(operate_name or "").strip() or None,
        action=(action or "").strip() or None,
        variable_input=(variable_name or "").strip() or None,
    )
    partial = {
        "device_code": device_code,
        "device_name": device_name,
        "variable_name": variable_name,
        "variable_value": variable_value,
        "action": action,
        "operate_name": operate_name,
    }

    # 若只给了「开门」这类口语、未显式 action，先规范化为目录标准动作名
    action_token = (action or variable_name or "").strip()
    if not res.action and action_token:
        hint = find_device_action_hint(action_token)
        if hint:
            res.action = str(hint.get("action") or action_token)

    # --- ① 设备消解：编码直查 / 名称打分 / 多台 HITL ---
    dc = (device_code or "").strip()
    dn = (device_name or "").strip()
    if not dc and not dn:
        res.missing.append("device")
    else:
        code, record, err, auto = _resolve_device_with_auto_select(
            device_code=dc,
            device_name=dn,
        )
        if err and err.startswith("__MULTIPLE_DEVICES__"):
            # 特殊哨兵串：重新拉列表生成下拉选项（不把错误原文直接给用户）
            query = dn or dc
            payload = build_device_list_payload(device_name=dn, search=dn, size=10)
            try:
                data = call_platform_api(
                    method="post",
                    path="/device/getDeviceList",
                    data=payload,
                )
                from platform_mcp.runtime.tools.device import _extract_device_records

                _, records = _extract_device_records(data)
                _, sorted_records, _ = _pick_device_by_score(query, records)
                res.interrupt = _build_device_select_interrupt(
                    query=query,
                    records=sorted_records,
                    partial=partial,
                )
                res.missing.append("device")
                return res
            except PlatformApiError as exc:
                return CommandResolution(
                    missing=["device"],
                    interrupt={
                        "type": "ask_params",
                        "tool": "send_device_cmd",
                        "message": str(exc),
                        "fields": _build_missing_fields_interrupt(["device"], partial)["fields"],
                    },
                )

        if err:
            res.missing.append("device")
            res.interrupt = _build_missing_fields_interrupt(["device"], partial)
            res.interrupt["message"] = err
            return res

        if code:
            res.device_code = code
            if record:
                res.device_record = record
                res.device_name = str(record.get("deviceName") or dn or code)
            if auto:
                res.auto_resolved.append("device")

    if "device" in res.missing and not res.interrupt:
        # 缺设备时：若播报类动作且正文未明确，同屏一并补「播报内容」
        missing_slots: list[MissingSlot] = ["device"]
        action_token = (res.action or action or "").strip()
        if action_requires_user_value(action_token) and not str(variable_value or "").strip():
            extracted = extract_user_value_from_text(
                action_token,
                user_text=user_text or action or variable_name or "",
            )
            if not extracted:
                missing_slots.append("value")
        res.interrupt = _build_missing_fields_interrupt(missing_slots, partial)
        return res

    assert res.device_code

    # --- ② 变量消解：显式 varName / 动作目录打分 / 多变量 HITL ---
    vn_resolved, var_input, var_err = _resolve_variable_from_hints(
        res.device_code,
        variable_name=(variable_name or "").strip(),
        action=(res.action or action or "").strip(),
    )
    if vn_resolved:
        res.variable_name = vn_resolved
        res.variable_input = var_input or variable_name or vn_resolved
        # 用户没写变量名、靠动作推断成功 → 记入 auto_resolved
        if not (variable_name or "").strip() and (res.action or action):
            res.auto_resolved.append("variable")
        elif (res.action or action) and _required_var_name_for_action(
            (res.action or action or "").strip()
        ):
            # 门控硬绑定成功也记为自动消解变量
            if "variable" not in res.auto_resolved:
                res.auto_resolved.append("variable")
    elif var_err and var_err.startswith("__MULTIPLE_VARIABLES__"):
        res.missing.append("variable")
        res.interrupt = _build_variable_select_interrupt(
            device_code=res.device_code,
            device_name=res.device_name or res.device_code,
            partial=partial,
        )
        return res
    elif var_err and var_err.startswith(_REQUIRED_VAR_UNSUPPORTED_PREFIX):
        # 门控等硬绑定失败：不弹变量选择，直接失败文案
        msg = var_err[len(_REQUIRED_VAR_UNSUPPORTED_PREFIX) :]
        res.missing.append("variable")
        res.interrupt = {
            "type": "error",
            "tool": "send_device_cmd",
            "message": msg,
            "fields": [],
        }
        return res
    else:
        res.missing.append("variable")
        # 平台返回的「多个可写变量」类文案 → 优先下拉，而非空白文本框
        if var_err and "多个" in var_err:
            res.interrupt = _build_variable_select_interrupt(
                device_code=res.device_code,
                device_name=res.device_name or res.device_code,
                partial=partial,
            )
            if res.interrupt:
                return res
        if not res.interrupt:
            res.interrupt = _build_missing_fields_interrupt(["variable"], partial)
            if var_err:
                res.interrupt["message"] = var_err
        return res

    # --- ③ 写入值：显式优先 → 口语抽取（播报等）→ 动作目录推断 ---
    vv = str(variable_value or "").strip()
    action_for_value = (res.action or action or variable_name or "").strip()
    if not vv:
        extracted = extract_user_value_from_text(
            action_for_value,
            user_text=user_text or action or variable_name or "",
        )
        if extracted:
            vv = extracted
            res.variable_value = vv
            res.auto_resolved.append("value")
        else:
            inferred = infer_value_from_action(
                action_for_value,
                user_text=user_text or action or variable_name or "",
            )
            if inferred is not None:
                vv = inferred
                res.variable_value = vv
                res.auto_resolved.append("value")
            else:
                res.missing.append("value")
                res.interrupt = _build_missing_fields_interrupt(["value"], partial)
                if action_requires_user_value(action_for_value):
                    res.interrupt["message"] = "请输入要播报的文字内容后再下发。"
                return res
    else:
        res.variable_value = vv

    # 操作说明默认值：便于平台审计「谁触发了什么」
    if not res.operate_name:
        act_label = res.action or "设备控制"
        disp = res.device_name or res.device_code or ""
        res.operate_name = f"AI助手{act_label}-{disp}".strip("-")

    # 三要素齐全：清空 missing / interrupt，调用方可直接 to_tool_args()
    res.missing = []
    res.interrupt = None
    return res


def pick_alternate_writable_variable(
    device_code: str,
    *,
    exclude_var: str,
    action: str,
) -> tuple[str | None, str | None]:
    """
    sendCmd 失败后，按动作语义从剩余可写变量中选备选 varName（供底层自动重试）。

    返回 (var_name, show_name_or_var)；无合适备选时 (None, None)。
    声明 requiredVarName 的动作（开门/关门）禁止换变量重试。
    """
    action_hint = find_device_action_hint(action)
    if not action_hint:
        return None, None
    if str(action_hint.get("requiredVarName") or "").strip():
        return None, None
    try:
        records = _fetch_device_variable_records(device_code)
    except PlatformApiError:
        return None, None

    exclude = (exclude_var or "").strip().lower()
    candidates = [r for r in records if _var_name_of(r) and _var_name_of(r).lower() != exclude]
    if not candidates:
        return None, None

    scored = sorted(
        ((_score_variable_for_action(item, action_hint), item) for item in candidates),
        key=lambda x: x[0],
        reverse=True,
    )
    top_score, top_item = scored[0]
    if top_score < _VARIABLE_TOP1_MIN_SCORE:
        return None, None
    vn = _var_name_of(top_item)
    sn = _show_name_of(top_item) or vn
    return (vn, sn) if vn else (None, None)
