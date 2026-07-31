"""
将 TypeScript 里的「模型 / 工具目录」导出为 JSON，供 Python Agent 后端读取。

【背景】
前后端共享一份「契约」：packages/agent-core/ 下的 .ts 文件是「唯一数据源」。
Python 不能直接 import TypeScript，所以用本脚本：
  1. 读 model-catalog.ts、tool-catalog.ts
  2. 用正则简单解析出字段
  3. 写出 app/models/catalog.json、app/tools/catalog.json
  4. 顺带调用另外两个脚本，导出导航路由和 API 索引

【如何运行？】
  cd services/platform-agent-service
  uv run python scripts/export_catalog.py

【Python 小白提示】
  - subprocess.run：在 Python 里启动另一个程序（这里是另一个 .py 脚本）
  - re 模块：正则表达式，用来从 .ts 文本里「抠」出字段值
  - json.dumps(..., ensure_ascii=False)：中文不转成 \\uXXXX 转义
"""

import json
import re
import shutil
import subprocess  # 启动子进程运行其他 Python 脚本
import sys  # sys.executable = 当前 Python 解释器路径
from pathlib import Path

# ---------------------------------------------------------------------------
# 路径：从本文件位置推算 monorepo 各目录
# ---------------------------------------------------------------------------

# platform-agent-service 根目录
SERVICE_ROOT = Path(__file__).resolve().parent.parent
# monorepo 根（services/ 的上一级）
REPO_ROOT = SERVICE_ROOT.parent.parent
SERVICES_ROOT = SERVICE_ROOT.parent

# TypeScript 源文件（契约层）
TS_MODEL_CATALOG = REPO_ROOT / "packages/agent-core/model-catalog.ts"
TS_TOOL_CATALOG = REPO_ROOT / "packages/agent-core/tool-catalog.ts"

# Python 侧输出的 JSON
OUT_MODEL_JSON = SERVICE_ROOT / "app/models/catalog.json"
OUT_TOOL_JSON = SERVICE_ROOT / "app/tools/catalog.json"
OUT_NAV_ROUTES_JSON = SERVICE_ROOT / "app/data/navigation_routes.json"
OUT_API_INDEX_JSON = SERVICE_ROOT / "app/data/platform_api_index.json"
# Platform MCP 数据目录
OUT_MCP_PKG_DATA = SERVICES_ROOT / "platform-mcp-server" / "platform_mcp" / "data"


def parse_ts_model_catalog(content: str) -> list[dict]:
    """
    从 model-catalog.ts 文本中解析 AGENT_MODEL_CATALOG 数组。

    注意：这是「简易解析」，用正则匹配，不是完整 TypeScript 编译器。
    Phase 0 字段足够用时采用此方式，避免引入 Node 依赖。

    参数:
        content: .ts 文件的完整字符串

    返回:
        模型条目列表，每项如 {"modelId": "...", "provider": "...", ...}

    异常:
        ValueError: 找不到 AGENT_MODEL_CATALOG 常量
    """
    # re.DOTALL：让 . 也能匹配换行符，以便跨行匹配数组内容
    match = re.search(
        r"export const AGENT_MODEL_CATALOG.*?=\s*\[(.*?)\];",
        content,
        re.DOTALL,
    )
    if not match:
        raise ValueError("未找到 AGENT_MODEL_CATALOG")

    items = []
    # 在每个 {...} 块里找字段（不含嵌套大括号的简单块）
    blocks = re.findall(r"\{[^{}]+\}", match.group(1), re.DOTALL)
    for block in blocks:
        item: dict = {}
        # 字符串字段：modelId: 'xxx' 或 "xxx"
        for key in (
            "modelId",
            "apiModelName",
            "provider",
            "labelKey",
            "scenarioKey",
        ):
            m = re.search(rf"{key}:\s*['\"]([^'\"]+)['\"]", block)
            if m:
                item[key] = m.group(1)  # group(1) 是第一个括号捕获的内容
        # 布尔字段：enabled: true / false
        for key in ("enabled", "isDefault", "supportsVision", "supportsAudio"):
            m = re.search(rf"{key}:\s*(true|false)", block)
            if m:
                item[key] = m.group(1) == "true"  # 字符串比较得到 bool
        if item.get("modelId"):
            items.append(item)
    return items


def parse_ts_tool_catalog(content: str) -> list[dict]:
    """
    从 tool-catalog.ts 解析完整 PLATFORM_TOOL_CATALOG manifest。

    含 parameters JSON Schema、side、risk_level 等，供 preflight / plan_confirm 读取。
    """
    from scripts.tool_catalog_parse import parse_ts_tool_catalog as _parse_full

    return _parse_full(content)


def export_navigation_routes():
    """
    调用 extract_navigation_routes.py，生成 navigation_routes.json。

    subprocess.run([解释器, 脚本路径]) 等价于在终端执行：
      python scripts/extract_navigation_routes.py
    check=False：子进程失败不抛异常（由子脚本自己打印错误）
    """
    script = SERVICE_ROOT / "scripts" / "extract_navigation_routes.py"
    if script.exists():
        subprocess.run([sys.executable, str(script)], check=False)


def sync_mcp_runtime_data() -> None:
    """将 catalog / 导航 / 设备动作目录同步到 platform_mcp/data（单一源）。"""
    OUT_MCP_PKG_DATA.mkdir(parents=True, exist_ok=True)
    pairs = [
        (OUT_TOOL_JSON, "catalog.json"),
        (SERVICE_ROOT / "app/data/navigation_routes.json", "navigation_routes.json"),
        (
            SERVICE_ROOT / "app/data/device_action_catalog.json",
            "device_action_catalog.json",
        ),
    ]
    for src, name in pairs:
        if not src.is_file():
            continue
        shutil.copy2(src, OUT_MCP_PKG_DATA / name)
        print(f"Synced {name} -> {OUT_MCP_PKG_DATA}")


def export_api_index():
    """调用 export_api_index.py，从 swagger 生成 platform_api_index.json。"""
    script = SERVICE_ROOT / "scripts" / "export_api_index.py"
    if script.exists():
        subprocess.run([sys.executable, str(script)], check=False)


def main():
    """
    主流程：导出模型 catalog → 工具 catalog → 导航路由 → API 索引。
    """
    # 1. 模型 catalog
    model_content = TS_MODEL_CATALOG.read_text(encoding="utf-8")
    models = parse_ts_model_catalog(model_content)
    OUT_MODEL_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_MODEL_JSON.write_text(
        json.dumps(models, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Exported {len(models)} models to {OUT_MODEL_JSON}")

    # 2. 工具 catalog（文件存在才导出）
    if TS_TOOL_CATALOG.exists():
        tool_content = TS_TOOL_CATALOG.read_text(encoding="utf-8")
        tools = parse_ts_tool_catalog(tool_content)
        payload = json.dumps(tools, ensure_ascii=False, indent=2)
        OUT_TOOL_JSON.parent.mkdir(parents=True, exist_ok=True)
        OUT_TOOL_JSON.write_text(payload, encoding="utf-8")
        print(f"Exported {len(tools)} tools (full manifest) to {OUT_TOOL_JSON}")

    # 3. 链式导出其他 JSON
    export_navigation_routes()
    export_api_index()
    sync_mcp_runtime_data()


if __name__ == "__main__":
    main()
