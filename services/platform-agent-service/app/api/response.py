"""
统一 JSON 响应封装模块（Response Envelope）

文件职责
--------
本模块定义 Agent 后端所有 **非 SSE 流式** 接口的 JSON 响应格式。
前端约定：HTTP 200 时仍须检查 body 中的 `code` 字段，`code === 0` 表示业务成功。

在 Agent 流程中的位置
--------------------
位于 API 层最底层，被 audit、sessions、transcribe、trace、models 等模块引用。
chat / resume 在参数校验失败时也会通过 `fail()` 构造 JSON 错误体。

如何被调用
----------
- 各 API 处理函数直接 `return ok(...)` 或 `return fail(...)` 返回 dict
- FastAPI 自动将 dict 序列化为 JSON 响应体
- 路由注册见 `app/main.py`，例如 `GET /api/agent/models` → `models.list_models()`

响应格式
--------
成功：{"code": 0, "data": <任意>, "message": "ok"}
失败：{"code": <非0>, "data": <详情或null>, "message": "<错误说明>"}
"""

# ---------------------------------------------------------------------------
# 标准库：类型注解用 Any 表示「任意 Python 对象」
# ---------------------------------------------------------------------------
from typing import Any

# ---------------------------------------------------------------------------
# 第三方：Pydantic 用于定义带类型校验的数据模型（类似 TypeScript 的 interface + 运行时校验）
# ---------------------------------------------------------------------------
from pydantic import BaseModel


class AgentApiResponse[T](BaseModel):
    """
    Agent API 统一响应体的 Pydantic 模型（主要用于类型文档与 IDE 提示）。

    泛型语法说明
    ------------
    `[T]` 是 Python 3.12+ 的泛型类写法，T 表示 `data` 字段的实际类型。
    例如 `AgentApiResponse[dict]` 表示 data 是字典。

    字段说明
    --------
    code : int
        业务状态码，0 为成功，非 0 为各类错误（见各 API 模块中的错误码定义）。
    data : T
        业务数据载荷，成功时放结果，失败时可放错误详情。
    message : str
        人类可读的状态描述，供前端展示或日志记录。
    """

    code: int
    data: T
    message: str


def ok(data: Any = None, message: str = "ok") -> dict[str, Any]:
    """
    构造成功响应字典。

    参数
    ----
    data : Any, 可选
        要返回给前端的业务数据，默认为 None。
    message : str, 可选
        成功提示文案，默认 "ok"。

    返回
    ----
    dict
        形如 {"code": 0, "data": data, "message": message} 的字典。

    异常
    ----
    本函数不抛出异常。
    """
    return {"code": 0, "data": data, "message": message}


def fail(code: int, message: str, data: Any = None) -> dict[str, Any]:
    """
    构造失败响应字典。

    参数
    ----
    code : int
        非零业务错误码，例如 40001（参数错误）、40404（资源不存在）等。
    message : str
        面向用户的错误摘要。
    data : Any, 可选
        附加错误详情（如字段名、堆栈摘要），可为 None。

    返回
    ----
    dict
        形如 {"code": code, "data": data, "message": message} 的字典。

    异常
    ----
    本函数不抛出异常。
    """
    return {"code": code, "data": data, "message": message}
