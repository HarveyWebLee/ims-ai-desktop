"""
供 uvicorn 热重载以「模块路径:变量」导入的 ASGI 应用。

``uvicorn.run("platform_mcp.asgi:app", reload=True)`` 必须用字符串导入，
不能直接传入 app 实例，否则热重载无效。
"""

from __future__ import annotations

from platform_mcp.server import mcp

# Streamable HTTP：与 main.run() 无 reload 路径一致（默认挂载 /mcp）
app = mcp.http_app(transport="streamable-http")
