---
name: desktop-chat-feature
description: >-
  开发或修复 Electron 桌面聊天能力（登录、SSE、HITL、Plan 步骤条、会话历史、
  Voice、client_action 降级）。在改 apps/desktop 或 packages/desktop-api 时使用。
---

# 桌面聊天功能技能

## 适用范围

- `apps/desktop/src/components/AiAssistant/**`
- `apps/desktop/src/services/AgentController.ts`
- `packages/desktop-api/**`

## 编码前

1. 确认是否触及：流式发送、resume、reject、abort、新会话、Plan、HITL Store
2. 读对称调用链，禁止只改报错点
3. 若改 SSE 事件字段：同步 `packages/shared-types` 与 parser

## 实现要点

- 状态：`streaming` / `pendingInterrupt` / `planSteps` 必须成对清理
- 登录 token：`@ims/desktop-api`；失效回登录页
- i18n：`locales/ai_assistant` 中英文同步
- UI：遵守 `.cursor/rules/desktop-ui-antd.mdc`（主题 Token、`App.useApp` / `@/antd/feedback`）
- M1：Plan 仅步骤条；不引入 BPMN 画布
- `client_action` navigate 等：跳过 + 用户可读提示

## 验证

```bash
bash scripts/desktop.sh   # 需 Agent :8008 / MCP :8010 已起
```

对照 `docs/desktop-m1-acceptance.md`：登录 → 对话 → HITL → 中止 → 新会话无残留。

## 禁止

- 桌面端直连达梦或实现 Agent 图逻辑
- 硬编码 Agent URL
- 半成品：只改 send 不改 abort/reject
