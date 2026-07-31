/**

 * @ims/agent-core — 大模型目录（唯一数据源）

 * 新增/下线模型只改此文件，并同步 @ims/shared-types AgentModelId

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

/** 默认对话模型 */

export const DEFAULT_AGENT_MODEL_ID: AgentModelId = "qwen3.7-plus";

/** 可选大模型目录 */

export const AGENT_MODEL_CATALOG: AgentModelCatalogItem[] = [
  {
    modelId: "qwen3.7-plus",

    apiModelName: "qwen3.7-plus",

    provider: "dashscope",

    labelKey: "aiAssistant.model.qwen3.7-plus",

    enabled: true,

    isDefault: true,

    scenarioKey: "aiAssistant.model.scenario.default",
  },

  {
    modelId: "qwen3.5-flash-2026-02-23",

    apiModelName: "qwen3.5-flash-2026-02-23",

    provider: "dashscope",

    labelKey: "aiAssistant.model.qwen3.5-flash-2026-02-23",

    enabled: true,

    scenarioKey: "aiAssistant.model.scenario.light",
  },

  {
    modelId: "qwen-plus-2025-07-28",

    apiModelName: "qwen-plus-2025-07-28",

    provider: "dashscope",

    labelKey: "aiAssistant.model.qwen-plus-2025-07-28",

    enabled: true,
  },

  {
    modelId: "qwen-long",

    apiModelName: "qwen-long",

    provider: "dashscope",

    labelKey: "aiAssistant.model.qwen-long",

    enabled: true,
  },

  {
    modelId: "qwen-mt-flash",

    apiModelName: "qwen-mt-flash",

    provider: "dashscope",

    labelKey: "aiAssistant.model.qwen-mt-flash",

    enabled: true,
  },

  {
    modelId: "qwen-math-turbo",

    apiModelName: "qwen-math-turbo",

    provider: "dashscope",

    labelKey: "aiAssistant.model.qwen-math-turbo",

    enabled: true,
  },

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
  },

  {
    modelId: "qwen3-32b",

    apiModelName: "qwen3-32b",

    provider: "dashscope",

    labelKey: "aiAssistant.model.qwen3-32b",

    enabled: true,
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
];

/** 获取已启用的模型列表 */

export function getEnabledModels(): AgentModelCatalogItem[] {
  return AGENT_MODEL_CATALOG.filter((m) => m.enabled);
}

/** 获取支持音频输入/转写的模型 */

export function getAudioModels(): AgentModelCatalogItem[] {
  return AGENT_MODEL_CATALOG.filter((m) => m.enabled && m.supportsAudio);
}

/** 按 modelId 查找 catalog 条目，非法 id 返回 undefined */

export function getCatalogItem(
  modelId: string,
): AgentModelCatalogItem | undefined {
  return AGENT_MODEL_CATALOG.find((m) => m.modelId === modelId && m.enabled);
}
