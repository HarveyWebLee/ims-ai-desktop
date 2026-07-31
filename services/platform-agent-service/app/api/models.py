"""
模型目录查询 API 模块

文件职责
--------
提供 `GET /api/agent/models` 接口的处理逻辑，返回当前 Agent 可用的 LLM 模型列表
及默认模型 ID，供前端 ModelSelector 组件渲染下拉选项。

在 Agent 流程中的位置
--------------------
位于对话流程的 **前置配置** 阶段：用户选择模型 → 前端在 `POST /api/agent/chat`
或 `POST /api/agent/resume` 请求体中携带 `model_id` → 后端校验 model_id 是否在 catalog 中。

如何被调用
----------
- 路由：`app/main.py` 中 `@app.get("/api/agent/models")` 绑定 `list_models()`
- 前端：App 侧栏加载时请求该接口，缓存模型列表
- 依赖：`app.models.catalog` 从 `catalog.json`（由 packages/agent-core 导出）读取模型配置
"""

# ---------------------------------------------------------------------------
# 本项目：统一成功响应封装
# ---------------------------------------------------------------------------
from app.api.response import ok

# ---------------------------------------------------------------------------
# 本项目：模型目录读取（默认模型 ID、已启用模型列表）
# ---------------------------------------------------------------------------
from app.models.catalog import get_default_model_id, get_enabled_models


async def list_models():
    """
    列出所有已启用的 Agent 模型及默认模型 ID。

    说明
    ----
    函数声明为 `async def`，与 FastAPI 其他路由处理函数风格一致；
    本函数内部无 I/O 等待，但 async 不影响正确性，FastAPI 可直接 await。

    参数
    ----
    无（无需 Authorization，模型目录为公开配置）。

    返回
    ----
    dict
        通过 `ok()` 包装的成功响应，data 结构为：
        {
            "defaultModelId": str,   # 未指定 model_id 时后端使用的默认值
            "models": [              # 已启用模型数组
                {
                    "modelId": str,
                    "label": str,    # 展示名，优先 labelKey，否则用 modelId
                    "provider": str  # 供应商标识，如 deepseek、dashscope
                },
                ...
            ]
        }

    异常
    ----
    本函数不主动抛出异常；catalog 读取失败时行为由 catalog 模块决定。
    """
    # 从 catalog.json 过滤出 enabled=true 的模型条目
    models = get_enabled_models()

    return ok(
        {
            # 前端未传 model_id 时 chat/resume 使用的默认模型
            "defaultModelId": get_default_model_id(),
            # 列表推导式：对 models 中每个字典 m 构造精简字段供前端展示
            "models": [
                {
                    "modelId": m["modelId"],
                    # dict.get(key, default)：键不存在时返回 default，避免 KeyError
                    "label": m.get("labelKey", m["modelId"]),
                    "provider": m["provider"],
                }
                for m in models
            ],
        }
    )
