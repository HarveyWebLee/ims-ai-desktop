---
name: add-agent-tool-e2e
description: >-
  新增或扩展 Platform MCP / Agent 工具的端到端流程（catalog → export → MCP handler →
  preflight → resume 对称路径 → 测试）。在用户要求加工具、改参数、改风险等级或 HITL 时使用。
---

# 新增工具 E2E（ims-ai-desktop）

## 0. 需求输入

- 工具名（snake_case）/ 用户视角目标 / 平台 API
- 必填参数 / 风险等级 / 缺参策略 / summary / 失败降级

## 1. 契约先行

1. 改 `packages/agent-core/tool-catalog.ts`（中文 description）
2. 导出：

```bash
cd services/platform-agent-service
python scripts/export_catalog.py
```

3. 确认 `services/platform-agent-service/app/tools/catalog.json` 与 MCP 侧 catalog 同步

## 2. MCP 实现

- 实现落在 `services/platform-mcp-server/`
- 统一 `ToolResult`（`@ims/shared-types`）：`ok` / `summary` / `data` / `client_action?` / `client_actions?`
- 禁止在 Agent 进程内新增业务 `@tool` 旁路

## 3. preflight / HITL

- 缺参 → 图内 `interrupt`（非图外 pending）
- 高风险 → 确认 interrupt
- resume 一律 `Command(resume=...)`

## 4. 对称路径

- `stream_chat` 与 `stream_resume`
- reject / cancel 清理 interrupt，不污染下一轮
- 桌面端 HITL 卡可解析新字段；`client_action` 无宿主时跳过降级

## 5. 验证

```bash
cd services/platform-agent-service
uv run check lint
uv run check typecheck
# 或仓库根：pnpm check:agent
pytest -q
```

并按 `docs/desktop-m1-acceptance.md` 手测一次相关对话。

## 自检

- [ ] catalog 与导出 JSON 同步
- [ ] 无双 HITL / 无达梦写
- [ ] chat / resume / reject 覆盖
