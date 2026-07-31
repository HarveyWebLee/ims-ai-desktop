# 迭代设想

本目录描述 **ims-ai-desktop** 后续方向，**不是**编码唯一依据（架构以 `docs/architecture/` 为准）。

## 当前基线（M1）

- Electron 登录 + SSE 对话 + HITL + Plan 步骤条
- Platform MCP `:8010` + Agent `:8008` + RAG
- Python 共享契约：`services/platform-contracts`（包名 `contracts`）；Agent **禁止** `import platform_mcp`
- 验收：[`../desktop-m1-acceptance.md`](../desktop-m1-acceptance.md)

## 架构债收口（已完成）

| 项                               | 状态 | 说明                                                                                  |
| -------------------------------- | ---- | ------------------------------------------------------------------------------------- |
| Agent ↔ MCP 编译边界             | ✅   | 抽出 `contracts`；工具执行仅 MCP HTTP；`tests/test_no_platform_mcp_import.py` 守卫    |
| AI-first 文档对齐                | ✅   | `00` / `03` / `08` 标明默认恒 `react`                                                 |
| ToolResult / client_actions      | ✅   | 已入 `@ims/shared-types` 与 `06-contracts`                                            |
| Gateway / 写工具权限 fail-closed | ✅   | 见 Gateway 鉴权与 `AGENT_TOOL_PERMISSION_FAIL_CLOSED`（以代码与 `.env.example` 为准） |

## Cursor Agent 对标（专项）

完整对比与分阶段优化计划见：

- [**cursor-agent-parity.md**](./cursor-agent-parity.md) — Cursor Harness 摘要、与本仓架构/实现差异、P0～P2 优化计划

摘要优先级：

| 阶段   | 焦点                                                            |
| ------ | --------------------------------------------------------------- |
| **P0** | 会话运行模式、工具子集注入、对称路径/HITL UX、错误降级          |
| **P1** | 运行时 Playbook、显式 Plan、轻量 Subagent、结果卡片、RAG 运营   |
| **P2** | 运行时 Hooks/审计、client_action 闭环、模型路由、长任务（可选） |

## 可选后续方向

| 方向             | 说明                                                        |
| ---------------- | ----------------------------------------------------------- |
| Cursor 能力对标  | 见 [cursor-agent-parity.md](./cursor-agent-parity.md)       |
| 工具与结构化卡片 | 高频工具结果卡片、Workspace 面板（含于 P1）                 |
| RAG 可运营化     | 知识库增删改查运营、实体同步可观测（含于 P1）               |
| 桌面 ↔ 平台联动  | 有宿主时执行 navigate / 告警详情等 client_action（含于 P2） |
| BPMN 编排 UI     | 未纳入；若开启需单独立项并补契约与验收                      |
