# 迭代设想

本目录描述 **ims-ai-desktop** 后续方向，**不是**编码唯一依据（架构以 `docs/architecture/` 为准）。

## 当前基线（M1）

- Electron 登录 + SSE 对话 + HITL + Plan 步骤条
- Platform MCP `:8010` + Agent `:8008` + RAG
- 验收：[`../desktop-m1-acceptance.md`](../desktop-m1-acceptance.md)

## 可选后续方向

| 方向             | 说明                                             |
| ---------------- | ------------------------------------------------ |
| 工具与结构化卡片 | 高频工具结果卡片、Workspace 面板                 |
| RAG 可运营化     | 知识库增删改查运营、实体同步可观测               |
| 桌面 ↔ 平台联动  | 有宿主时执行 navigate / 告警详情等 client_action |
| BPMN 编排 UI     | 未纳入；若开启需单独立项并补契约与验收           |
