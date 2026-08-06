/**
 * @ims/agent-core — 大模型目录（唯一数据源）
 * 新增/下线模型只改此文件，并同步 @ims/shared-types AgentModelId
 * 改完后：cd services/platform-agent-service && uv run python scripts/export_catalog.py
 */
import type { AgentModelId, AgentModelProvider } from "@ims/shared-types";

export interface AgentModelCatalogItem {
  modelId: AgentModelId;
  /** 调用厂商 API 时的 model 参数 */
  apiModelName: string;
  provider: AgentModelProvider;
  /** i18n key：aiAssistant.model.{modelId} */
  labelKey: string;
  enabled: boolean;
  isDefault?: boolean;
  scenarioKey?: string;
  supportsVision?: boolean;
  supportsAudio?: boolean;
}

/** 自动路由占位（非厂商模型；后端按意图从已启用 catalog 中选型） */
export const AUTO_AGENT_MODEL_ID = "auto" as const;
export type AgentModelSelectionId = AgentModelId | typeof AUTO_AGENT_MODEL_ID;

/** 默认对话模型（须为 enabled + isDefault） */
export const DEFAULT_AGENT_MODEL_ID: AgentModelId = "qwen3-32b";

/** 可选大模型目录 */
export const AGENT_MODEL_CATALOG: AgentModelCatalogItem[] = [
  {
    modelId: "qwen3.5-35b-a3b",
    apiModelName: "qwen3.5-35b-a3b",
    provider: "dashscope",
    labelKey: "aiAssistant.model.qwen3.5-35b-a3b",
    enabled: true,
  },
  {
    modelId: "qwen3-8b",
    apiModelName: "qwen3-8b",
    provider: "dashscope",
    labelKey: "aiAssistant.model.qwen3-8b",
    enabled: true,
    scenarioKey: "aiAssistant.model.scenario.light",
  },
  {
    modelId: "qwen3-32b",
    apiModelName: "qwen3-32b",
    provider: "dashscope",
    labelKey: "aiAssistant.model.qwen3-32b",
    enabled: true,
    isDefault: true,
    scenarioKey: "aiAssistant.model.scenario.default",
  },
  {
    modelId: "qwen3-coder-plus",
    apiModelName: "qwen3-coder-plus",
    provider: "dashscope",
    labelKey: "aiAssistant.model.qwen3-coder-plus",
    enabled: true,
  },
  {
    modelId: "qwen3-coder-480b-a35b-instruct",
    apiModelName: "qwen3-coder-480b-a35b-instruct",
    provider: "dashscope",
    labelKey: "aiAssistant.model.qwen3-coder-480b-a35b-instruct",
    enabled: true,
  },
  {
    modelId: "deepseek-v4-flash",
    apiModelName: "deepseek-v4-flash",
    provider: "deepseek",
    labelKey: "aiAssistant.model.deepseek-v4-flash",
    enabled: true,
    scenarioKey: "aiAssistant.model.scenario.light",
  },
  {
    modelId: "deepseek-r1-distill-qwen-7b",
    apiModelName: "deepseek-r1-distill-qwen-7b",
    provider: "dashscope",
    labelKey: "aiAssistant.model.deepseek-r1-distill-qwen-7b",
    enabled: true,
    scenarioKey: "aiAssistant.model.scenario.light",
  },
  {
    modelId: "deepseek-r1-distill-qwen-32b",
    apiModelName: "deepseek-r1-distill-qwen-32b",
    provider: "dashscope",
    labelKey: "aiAssistant.model.deepseek-r1-distill-qwen-32b",
    enabled: true,
  },
  {
    modelId: "qwen3-vl-flash-2025-10-15",
    apiModelName: "qwen3-vl-flash-2025-10-15",
    provider: "dashscope",
    labelKey: "aiAssistant.model.qwen3-vl-flash-2025-10-15",
    enabled: true,
    supportsVision: true,
  },
  {
    modelId: "qwen3-vl-8b-thinking",
    apiModelName: "qwen3-vl-8b-thinking",
    provider: "dashscope",
    labelKey: "aiAssistant.model.qwen3-vl-8b-thinking",
    enabled: true,
    supportsVision: true,
  },
  {
    modelId: "qwen3-vl-30b-a3b-thinking",
    apiModelName: "qwen3-vl-30b-a3b-thinking",
    provider: "dashscope",
    labelKey: "aiAssistant.model.qwen3-vl-30b-a3b-thinking",
    enabled: true,
    supportsVision: true,
  },
  {
    modelId: "qwen3-vl-32b-thinking",
    apiModelName: "qwen3-vl-32b-thinking",
    provider: "dashscope",
    labelKey: "aiAssistant.model.qwen3-vl-32b-thinking",
    enabled: true,
    supportsVision: true,
  },
  {
    modelId: "qwen3-vl-235b-a22b-thinking",
    apiModelName: "qwen3-vl-235b-a22b-thinking",
    provider: "dashscope",
    labelKey: "aiAssistant.model.qwen3-vl-235b-a22b-thinking",
    enabled: true,
    supportsVision: true,
  },
  {
    modelId: "qwen-vl-plus",
    apiModelName: "qwen-vl-plus",
    provider: "dashscope",
    labelKey: "aiAssistant.model.qwen-vl-plus",
    enabled: true,
    supportsVision: true,
  },
  {
    modelId: "qwen-vl-ocr-latest",
    apiModelName: "qwen-vl-ocr-latest",
    provider: "dashscope",
    labelKey: "aiAssistant.model.qwen-vl-ocr-latest",
    enabled: true,
    supportsVision: true,
  },
  {
    modelId: "qwen3.7-flash-2026-07-15",
    apiModelName: "qwen3.7-flash-2026-07-15",
    provider: "dashscope",
    labelKey: "aiAssistant.model.qwen3.7-flash-2026-07-15",
    enabled: true,
    scenarioKey: "aiAssistant.model.scenario.light",
  },
  {
    modelId: "qwen-plus-0112",
    apiModelName: "qwen-plus-0112",
    provider: "dashscope",
    labelKey: "aiAssistant.model.qwen-plus-0112",
    enabled: true,
  },
  {
    modelId: "qwen-plus",
    apiModelName: "qwen-plus",
    provider: "dashscope",
    labelKey: "aiAssistant.model.qwen-plus",
    enabled: true,
  },
  {
    modelId: "qwen-turbo",
    apiModelName: "qwen-turbo",
    provider: "dashscope",
    labelKey: "aiAssistant.model.qwen-turbo",
    enabled: true,
    scenarioKey: "aiAssistant.model.scenario.light",
  },
  {
    modelId: "qwen3-next-80b-a3b-thinking",
    apiModelName: "qwen3-next-80b-a3b-thinking",
    provider: "dashscope",
    labelKey: "aiAssistant.model.qwen3-next-80b-a3b-thinking",
    enabled: true,
  },
  {
    modelId: "qwen3.5-27b",
    apiModelName: "qwen3.5-27b",
    provider: "dashscope",
    labelKey: "aiAssistant.model.qwen3.5-27b",
    enabled: true,
  },
  {
    modelId: "tongyi-xiaomi-analysis-flash",
    apiModelName: "tongyi-xiaomi-analysis-flash",
    provider: "dashscope",
    labelKey: "aiAssistant.model.tongyi-xiaomi-analysis-flash",
    enabled: true,
    scenarioKey: "aiAssistant.model.scenario.light",
  },
  {
    modelId: "qwen3-vl-flash",
    apiModelName: "qwen3-vl-flash",
    provider: "dashscope",
    labelKey: "aiAssistant.model.qwen3-vl-flash",
    enabled: true,
    supportsVision: true,
  },
  {
    modelId: "qwen3-14b",
    apiModelName: "qwen3-14b",
    provider: "dashscope",
    labelKey: "aiAssistant.model.qwen3-14b",
    enabled: true,
  },
  {
    modelId: "qwen3-max-2025-09-23",
    apiModelName: "qwen3-max-2025-09-23",
    provider: "dashscope",
    labelKey: "aiAssistant.model.qwen3-max-2025-09-23",
    enabled: true,
  },
  {
    modelId: "qwen-plus-2025-12-01",
    apiModelName: "qwen-plus-2025-12-01",
    provider: "dashscope",
    labelKey: "aiAssistant.model.qwen-plus-2025-12-01",
    enabled: true,
  },
  {
    modelId: "qwen-plus-character",
    apiModelName: "qwen-plus-character",
    provider: "dashscope",
    labelKey: "aiAssistant.model.qwen-plus-character",
    enabled: true,
  },
  {
    modelId: "qwen-flash-character",
    apiModelName: "qwen-flash-character",
    provider: "dashscope",
    labelKey: "aiAssistant.model.qwen-flash-character",
    enabled: true,
    scenarioKey: "aiAssistant.model.scenario.light",
  },
  {
    modelId: "qwen3-30b-a3b-instruct-2507",
    apiModelName: "qwen3-30b-a3b-instruct-2507",
    provider: "dashscope",
    labelKey: "aiAssistant.model.qwen3-30b-a3b-instruct-2507",
    enabled: true,
  },
  {
    modelId: "qwen-flash",
    apiModelName: "qwen-flash",
    provider: "dashscope",
    labelKey: "aiAssistant.model.qwen-flash",
    enabled: true,
    scenarioKey: "aiAssistant.model.scenario.light",
  },
  {
    modelId: "qwen-flash-2025-07-28",
    apiModelName: "qwen-flash-2025-07-28",
    provider: "dashscope",
    labelKey: "aiAssistant.model.qwen-flash-2025-07-28",
    enabled: true,
    scenarioKey: "aiAssistant.model.scenario.light",
  },
  {
    modelId: "qwen3-235b-a22b-instruct-2507",
    apiModelName: "qwen3-235b-a22b-instruct-2507",
    provider: "dashscope",
    labelKey: "aiAssistant.model.qwen3-235b-a22b-instruct-2507",
    enabled: true,
  },
  {
    modelId: "qwen3.5-plus-2026-04-20",
    apiModelName: "qwen3.5-plus-2026-04-20",
    provider: "dashscope",
    labelKey: "aiAssistant.model.qwen3.5-plus-2026-04-20",
    enabled: true,
  },
  {
    modelId: "qwen-plus-1220",
    apiModelName: "qwen-plus-1220",
    provider: "dashscope",
    labelKey: "aiAssistant.model.qwen-plus-1220",
    enabled: true,
  },
  {
    modelId: "qwen3.5-122b-a10b",
    apiModelName: "qwen3.5-122b-a10b",
    provider: "dashscope",
    labelKey: "aiAssistant.model.qwen3.5-122b-a10b",
    enabled: true,
  },
  {
    modelId: "qwen3-max",
    apiModelName: "qwen3-max",
    provider: "dashscope",
    labelKey: "aiAssistant.model.qwen3-max",
    enabled: true,
  },
  {
    modelId: "qwen3.5-plus-2026-02-15",
    apiModelName: "qwen3.5-plus-2026-02-15",
    provider: "dashscope",
    labelKey: "aiAssistant.model.qwen3.5-plus-2026-02-15",
    enabled: true,
  },
  {
    modelId: "qwen3-235b-a22b-thinking-2507",
    apiModelName: "qwen3-235b-a22b-thinking-2507",
    provider: "dashscope",
    labelKey: "aiAssistant.model.qwen3-235b-a22b-thinking-2507",
    enabled: true,
  },
  {
    modelId: "qwen3.7-max-2026-06-08",
    apiModelName: "qwen3.7-max-2026-06-08",
    provider: "dashscope",
    labelKey: "aiAssistant.model.qwen3.7-max-2026-06-08",
    enabled: true,
  },
  {
    modelId: "qwen3.7-max-preview",
    apiModelName: "qwen3.7-max-preview",
    provider: "dashscope",
    labelKey: "aiAssistant.model.qwen3.7-max-preview",
    enabled: true,
  },
  {
    modelId: "qwen3.6-max-preview",
    apiModelName: "qwen3.6-max-preview",
    provider: "dashscope",
    labelKey: "aiAssistant.model.qwen3.6-max-preview",
    enabled: true,
  },
];

/** 获取已启用的模型列表 */
export function getEnabledModels(): AgentModelCatalogItem[] {
  return AGENT_MODEL_CATALOG.filter((m) => m.enabled);
}

/** 获取支持音频输入/转写的模型 */
export function getAudioModels(): AgentModelCatalogItem[] {
  return AGENT_MODEL_CATALOG.filter((m) => m.enabled && m.supportsAudio);
}

/** 按 modelId 查找已启用条目；非法或已禁用返回 undefined */
export function getCatalogItem(modelId: string): AgentModelCatalogItem | undefined {
  return AGENT_MODEL_CATALOG.find((m) => m.modelId === modelId && m.enabled);
}

/** 是否为 Auto 路由选择 */
export function isAutoModelSelection(id: string | null | undefined): boolean {
  return (id || "").trim() === AUTO_AGENT_MODEL_ID;
}
