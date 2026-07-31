# 桌面端 M1 手工验收

本仓独立验收清单。编码架构以 [`docs/architecture/`](./architecture/00-overview.md) 为准。

## 范围

| 能力          | M1 要求                                      |
| ------------- | -------------------------------------------- |
| 简易登录      | 调平台 `/api/app/auth/login`，token 本地存储 |
| SSE 对话      | chat / 中止 / 会话历史                       |
| HITL          | 基础确认 / 缺参表单 / resume / reject        |
| Plan          | 步骤条展示                                   |
| client_action | 无宿主时跳过并给出明确降级                   |

## 建议验证步骤

1. `bash scripts/up.sh` → `bash scripts/all.sh`
2. 桌面端登录成功，可发消息并收到 SSE 流式回复
3. 触发需确认工具 → HITL 卡出现 → 批准续跑 / 拒绝后状态清理
4. 中止流式：loading 结束，无残留 streaming
5. 新会话 / 切换历史：无上一轮 Plan / interrupt 污染
6. `curl -s localhost:8008/health` 正常；MCP `:8010` 可达

## 改动类型与必测对照

| 改动类型                     | 必测                         |
| ---------------------------- | ---------------------------- |
| SSE / AgentController parser | 对话流式、error envelope     |
| HITL / resume / reject       | 批准、拒绝、同 thread 下一轮 |
| Plan 步骤                    | 展示与清理                   |
| catalog / MCP 工具           | export → MCP → 一次真实调用  |
| 登录 / token                 | 失效后回登录页               |
| 达梦 / 实体同步              | 仅 SELECT；无写语句          |
