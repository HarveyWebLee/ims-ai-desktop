---
name: agent-feature-delivery
description: >-
  面向 ims-ai-desktop（桌面端 + Agent + MCP）的功能交付流程。
  在新增/修改 Agent、HITL、SSE、Plan、MCP 工具或桌面聊天能力时使用，
  强制影响面清单、对称路径与回归说明。
---

# Agent / 桌面端功能交付

当用户提出「新增/修改功能」时按本流程执行。

## 0) 需求边界

- 一句话复述目标（业务价值 + 成功标准）
- 明确是否涉及：`chat/resume/reject`、新工具/事件、状态生命周期、桌面 UI

## 1) 编码前影响面（必须写出）

1. 直接改动文件（`apps/desktop` / `services/*` / `packages/*`）
2. 对称路径（chat / resume / reject / abort / 新会话）
3. 状态（checkpoint interrupt、`session_store`、桌面 Store；**无** `pending_*` HITL）
4. 契约（SSE / ToolResult / catalog / shared-types）
5. 测试与验收（`docs/desktop-m1-acceptance.md`）

## 2) 实现策略优先级

1. 复用父图 `parent_graph` / `stream_parent_graph` 与桌面 SSE 主链
2. 在既有模块扩展（禁止旁路）
3. 破坏性收敛须同步契约、测试与文档
4. 最后才新增模块
5. 桌面端 M1：不擅自加 BPMN 抽屉

## 3) 编码与验证

- LangGraph 变更：先 `docs-langchain` 再编码
- Agent：`cd services/platform-agent-service && uv run check lint && uv run check typecheck`（或根目录 `pnpm check:agent`）
- 行为变化：补测试或更新现有测试
- 桌面：按 M1 验收手测关键路径

## 4) 交付说明

- 改了什么 / 为什么 / 可能影响 / 验证结果与未覆盖项

## 5) 禁止

- 只改单一路径（例如只改 chat）
- 图外 `pending_*` HITL 或 ReAct 双轨
- 对平台达梦非 SELECT
- 未验证却声称「全部完成」
