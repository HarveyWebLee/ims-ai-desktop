# platform_mcp 包布局

| 路径        | 说明                                                             |
| ----------- | ---------------------------------------------------------------- |
| `runtime/`  | **工具执行实现**（唯一业务源）                                   |
| `data/`     | catalog / navigation / device_action（`export_catalog.py` 同步） |
| `server.py` | FastMCP 注册与 HTTP                                              |
| `config.py` | 端口 / PLATFORM_API_BASE                                         |

已删除空占位目录 `catalog/`、`tools/`（勿再创建）。
