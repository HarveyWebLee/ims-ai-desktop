"""
模型路由模块：根据 model_id 创建 LangChain ChatOpenAI 实例

文件职责
--------
把目录里的 ``modelId`` 变成可真正发请求的 ``ChatOpenAI``（OpenAI 兼容协议）。
并提供「有没有真实 Key」校验，供 /health 与对话入口使用。

白话概念
--------
前端选了「通义 qwen3-32b」→ 本模块查 catalog → 取出 provider=dashscope →
拼上 DASHSCOPE_API_KEY 与兼容 base_url → 返回流式 Chat 模型给 LangGraph。

在 Agent 流程中的位置
--------------------
  stream_chat / agent_factory
    → resolve_chat_model(model_id)
  启动与健康检查 / 对话入口
    → has_real_model_credentials() / require_model_credentials()

设计要点
--------
- 懒加载 ``langchain_openai``：无 Key 时服务仍可启动，但对话会直接报错
- provider → base_url + api_key 映射
- 未配置密钥时抛出明确异常，不再提供 Mock 回复
"""

from __future__ import annotations

from app.config import settings  # 各厂商 API Key 等
from app.models.catalog import get_catalog_item  # 按 modelId 查目录项


class ModelCredentialsError(RuntimeError):
    """未配置大模型 API Key，无法调用真实 LLM。"""


def _provider_base_url(provider: str) -> str:
    """
    根据 provider 名称返回 OpenAI 兼容 API 的 base_url。

    多数国内大模型提供 OpenAI 兼容接口，LangChain ChatOpenAI 可直接对接。
    """
    mapping = {
        "deepseek": "https://api.deepseek.com/v1",
        "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    }
    return mapping.get(provider, "")


def _provider_api_key(provider: str) -> str:
    """
    从 settings 读取对应厂商的 API Key 字符串。
    """
    mapping = {
        "deepseek": settings.deepseek_api_key,
        "dashscope": settings.dashscope_api_key,
    }
    return mapping.get(provider, "")


def resolve_chat_model(model_id: str, *, streaming: bool = True):
    """
    根据 catalog 中的 model_id 创建并返回 ChatOpenAI 实例。

    参数：
        model_id: 目录中的 modelId，如 "qwen3-32b"
        streaming: 是否允许 token 流式；门控内 IR 等内部调用须 False

    返回：
        langchain_openai.ChatOpenAI 实例

    异常：
        ValueError — model_id 不存在/已禁用，或缺少对应厂商 API Key
    """
    # 延迟导入：避免启动时强制依赖 langchain_openai
    from langchain_openai import ChatOpenAI

    item = get_catalog_item(model_id)
    if not item:
        raise ValueError(f"model_id 不在模型目录中或已禁用: {model_id}")

    provider = item["provider"]
    api_key = _provider_api_key(provider)
    base_url = _provider_base_url(provider)

    if not api_key:
        env_name = {
            "deepseek": "DEEPSEEK_API_KEY",
            "dashscope": "DASHSCOPE_API_KEY",
        }.get(provider, f"{provider.upper()}_API_KEY")
        raise ValueError(
            f"未配置 {provider} API Key（环境变量 {env_name}）。"
            "请在 platform-agent-service/.env 中填写后重启服务。"
        )

    from pydantic import SecretStr

    return ChatOpenAI(
        model=item.get("apiModelName", item["modelId"]),  # 实际 API 模型名可能与 modelId 不同
        base_url=base_url,
        api_key=SecretStr(api_key),
        streaming=streaming,
        disable_streaming=not streaming,
    )


def has_real_model_credentials() -> bool:
    """
    检查是否配置了任意一个厂商的真实 API Key。

    用于判断是否具备调用真实 LLM 的条件。
    """
    return bool(settings.deepseek_api_key or settings.dashscope_api_key)


def require_model_credentials() -> None:
    """
    未配置任意 LLM API Key 时抛出明确异常。

    对话 / 续跑入口应在调用模型前调用本函数，避免静默失败。
    """
    if has_real_model_credentials():
        return
    raise ModelCredentialsError(
        "未配置大模型 API Key。请在 platform-agent-service/.env 中设置 "
        "DEEPSEEK_API_KEY 或 DASHSCOPE_API_KEY 后重启服务再试。"
    )
