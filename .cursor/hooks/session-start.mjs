#!/usr/bin/env node
/**
 * 会话开始提醒：对齐 ims-ai-desktop 架构与质量门禁。
 */
const context = [
  "【ims-ai-desktop 开发提醒】",
  "- 仓结构：apps/desktop + services/{platform-agent-service,platform-mcp-server} + packages/*",
  "- 联调：bash scripts/up.sh && bash scripts/all.sh（MCP:8010 → Agent:8008 → Electron）",
  "- 先输出影响面：chat/resume/reject/状态/SSE 契约/桌面 Store",
  "- 涉及 LangChain/LangGraph：先 docs-langchain 再编码，落入父图主链",
  "- 禁止 pending_* HITL、ReAct 双轨、平台达梦非 SELECT",
  "- 桌面端 M1：无 BPMN 抽屉；navigate 等 client_action 可跳过降级",
  "- Agent 变更后：cd services/platform-agent-service && uv run check lint && uv run check typecheck",
  "- 验收对照：docs/desktop-m1-acceptance.md",
].join("\n");

process.stdout.write(JSON.stringify({ additional_context: context }));
