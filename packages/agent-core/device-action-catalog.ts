/**
 * 设备控制口语动作目录（与 platform-agent-service/app/data/device_action_catalog.json 同步）
 *
 * 用途：LLM / Resolver 将「开门」「关门」「播报」等抽象意图映射为变量检索提示与默认写入值。
 * 最终 varName 仍须通过 query_device_variables / getVarListByCode 在目标设备上验证。
 */

/** 单条动作语义定义 */
export interface DeviceActionHint {
  /** 标准动作名（展示用） */
  action: string;
  /** 口语别名 */
  aliases: string[];
  /** 变量 showName/varName 检索关键词（按优先级尝试） */
  variableHints: string[];
  /**
   * 硬绑定目标 varName：若设置，消解时必须精确命中该可写变量，
   * 禁止模糊打分与失败后换变量重试（如开门/关门 → status_door_control，播报 → play）
   */
  requiredVarName?: string;
  /** 硬绑定变量中文名（失败提示用） */
  requiredVarLabel?: string;
  /**
   * 写入值必须由使用者明确给出（不可从 open/close/default 推断）。
   * 缺省时 HITL 补填；用于广播播报等内容型下发。
   */
  requireUserValue?: boolean;
  /** 子系统/设备类型提示（辅助设备 search） */
  subSystemHints?: string[];
  /** 默认写入值及口语映射（requireUserValue 时可省略） */
  valueHints?: {
    default?: string;
    open?: string;
    close?: string;
    [key: string]: string | undefined;
  };
}

/** 设备控制动作目录（唯一数据源，与 backend device_action_catalog.json 同步） */
export const DEVICE_ACTION_CATALOG: DeviceActionHint[] = [
  {
    action: "开门",
    aliases: ["打开门", "远程开门", "开锁", "开启门禁", "开闸"],
    variableHints: ["status_door_control", "门控制状态"],
    requiredVarName: "status_door_control",
    requiredVarLabel: "门控制状态",
    subSystemHints: ["门禁", "门控"],
    valueHints: { default: "1", open: "1", close: "0" },
  },
  {
    action: "关门",
    aliases: ["关闭门", "锁门", "关闸", "关闭门禁"],
    variableHints: ["status_door_control", "门控制状态"],
    requiredVarName: "status_door_control",
    requiredVarLabel: "门控制状态",
    subSystemHints: ["门禁", "门控"],
    valueHints: { default: "0", open: "1", close: "0" },
  },
  {
    action: "开启",
    aliases: ["打开", "启动", "开"],
    variableHints: ["开关", "控制", "启停", "switch", "status"],
    valueHints: { default: "1", open: "1", close: "0" },
  },
  {
    action: "关闭",
    aliases: ["关掉", "停止", "关"],
    variableHints: ["开关", "控制", "启停", "switch", "status"],
    valueHints: { default: "0", open: "1", close: "0" },
  },
  // 放在「关闭」之后，避免「关闭广播」被别名「广播」误命中为播报
  {
    action: "播报",
    aliases: [
      "下发广播",
      "广播播报",
      "语音播报",
      "播放广播",
      "广播通知",
      "广播",
    ],
    variableHints: ["play", "播报"],
    requiredVarName: "play",
    requiredVarLabel: "播报",
    requireUserValue: true,
    subSystemHints: ["广播"],
  },
];

/** 按口语 token 查找动作定义（精确 + 别名 + 包含匹配） */
export function findDeviceActionHint(
  token: string,
): DeviceActionHint | undefined {
  const t = (token || "").trim();
  if (!t) return undefined;
  for (const hint of DEVICE_ACTION_CATALOG) {
    if (hint.action === t) return hint;
    if (hint.aliases.some((a) => a === t)) return hint;
  }
  for (const hint of DEVICE_ACTION_CATALOG) {
    if (t.includes(hint.action) || hint.aliases.some((a) => t.includes(a))) {
      return hint;
    }
  }
  return undefined;
}
