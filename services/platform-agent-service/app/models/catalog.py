"""
模型目录模块：维护 Agent 可选用的大语言模型列表

文件职责
--------
提供「前端下拉 + 后端路由」共用的模型清单：按 modelId 查找、取默认模型、列已启用项。

白话概念
--------
模型目录 = 一张「可选 AI 大脑」名单（通义、DeepSeek…）。
真正改名单应改 TypeScript ``packages/agent-core/model-catalog.ts``，
再跑 ``scripts/export_catalog.py`` 生成同目录 ``catalog.json``。

在 Agent 流程中的位置
--------------------
  GET /api/agent/models → get_enabled_models()
  POST /chat 校验 model_id → get_catalog_item()
  建 ChatOpenAI → router.resolve_chat_model() 再读本目录

数据来源优先级
--------------
1. 同目录 ``catalog.json``（export 产物）
2. 内置 ``_BUILTIN_CATALOG``（与 TS 源保持一致的兜底快照）

每个模型项常见字段：modelId、provider、apiModelName、enabled、isDefault、labelKey。
"""

from __future__ import annotations

import json  # 读取 catalog.json
from pathlib import Path  # 跨平台路径操作
from typing import Any

# catalog.json 与当前 py 文件同目录
_CATALOG_PATH = Path(__file__).parent / "catalog.json"

# 当 catalog.json 不存在时的兜底默认模型 ID（须与 TS enabled 默认一致）
DEFAULT_MODEL_ID = "qwen3.5-35b-a3b"

# 与 TypeScript AGENT_MODEL_CATALOG 保持一致的内置快照（精简兜底）
# 修改模型列表时应同步更新 TS 源文件并运行 export_catalog.py
_BUILTIN_CATALOG: list[dict[str, Any]] = [
    {
        "modelId": "qwen3.5-35b-a3b",
        "apiModelName": "qwen3.5-35b-a3b",
        "provider": "dashscope",
        "labelKey": "aiAssistant.model.qwen3.5-35b-a3b",
        "enabled": True,
        "isDefault": True,
        "scenarioKey": "aiAssistant.model.scenario.default",
    },
    {
        "modelId": "deepseek-v4-flash",
        "apiModelName": "deepseek-v4-flash",
        "provider": "deepseek",
        "labelKey": "aiAssistant.model.deepseek-v4-flash",
        "enabled": True,
        "scenarioKey": "aiAssistant.model.scenario.light",
    },
    {
        "modelId": "qwen-flash",
        "apiModelName": "qwen-flash",
        "provider": "dashscope",
        "labelKey": "aiAssistant.model.qwen-flash",
        "enabled": True,
        "scenarioKey": "aiAssistant.model.scenario.light",
    },
]


def load_catalog() -> list[dict[str, Any]]:
    """
    加载完整模型目录。

    优先读取 catalog.json；文件不存在则返回内置列表。
    """
    if _CATALOG_PATH.exists():
        return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    return _BUILTIN_CATALOG


def get_enabled_models() -> list[dict[str, Any]]:
    """
    返回所有 enabled=True 的模型项（供前端 ModelSelector 等使用）。
    """
    return [m for m in load_catalog() if m.get("enabled", True)]


def get_catalog_item(model_id: str) -> dict[str, Any] | None:
    """
    按 modelId 查找单个已启用的模型配置。

    参数：
        model_id: 如 "qwen3.5-35b-a3b"

    返回：
        模型 dict，未找到或已禁用则 None
    """
    for item in load_catalog():
        if item.get("modelId") == model_id and item.get("enabled", True):
            return item
    return None


def get_default_model_id() -> str:
    """
    返回目录中标记 isDefault 且 enabled 的 modelId；
    否则回退首个已启用模型，再否则 DEFAULT_MODEL_ID。
    """
    for item in load_catalog():
        if item.get("isDefault") and item.get("enabled", True):
            return str(item["modelId"])
    enabled = get_enabled_models()
    if enabled:
        return str(enabled[0]["modelId"])
    return DEFAULT_MODEL_ID
