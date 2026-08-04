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
3. 触发需确认工具 → HITL 卡出现 → 批准续跑 / 拒绝后状态清理（拒绝后卡片显示「已拒绝」，可继续发新消息）
4. 中止流式：点停止按钮 → loading 结束，无残留 streaming / HITL / running 工具
5. 新会话 / 切换历史：无上一轮 Plan / interrupt 污染；有 pending interrupt 的历史会话显示「可续跑」并可继续确认
6. MCP 不可达时：明确「MCP 不可用」类错误提示（非 unknown）
7. `curl -s localhost:8008/health` 正常；MCP `:8010` 可达
8. Playbook（可选）：发「处理未确认告警」/「导出告警」→ Agent 按规程查询/导出（步骤可复现；改 `app/playbooks` 后重启生效）
9. 先计划：打开「先计划」开关 → 发「查近三天告警然后导出」→ 出现 plan_confirm → 批准后才执行导出
10. Subagent 检索（可选）：问产品/流程类知识 → `retrieve_knowledge` 工具结果为摘要（非大段原文），主回复仍连贯
11. 结果卡片：`query_alarms` 查表；`query_devices` 设备列表（点行可让助手查详情）；`download_file` 导出结果卡（含取消态）
12. RAG 运营（可选）：设置 → 知识与术语 → 文档规程（统计/展开预览/上传/下载）；实体术语（统计/试检索设备变量/同步）

## 残留态矩阵（P0）

| 路径        | pendingInterrupt | interrupt 块    | Plan 未完成步 | loading |
| ----------- | ---------------- | --------------- | ------------- | ------- |
| Stop/abort  | 清               | 终态 aborted    | skipped       | 关      |
| reject      | 清               | 终态 rejected   | skipped       | 关      |
| 新消息顶替  | 清               | 终态 superseded | skipped       | 新回合  |
| resume 批准 | 清块后续跑       | 清后执行        | 推进          | 流式    |

## 改动类型与必测对照

| 改动类型                     | 必测                         |
| ---------------------------- | ---------------------------- |
| SSE / AgentController parser | 对话流式、error envelope     |
| HITL / resume / reject       | 批准、拒绝、同 thread 下一轮 |
| Plan 步骤                    | 展示与清理                   |
| catalog / MCP 工具           | export → MCP → 一次真实调用  |
| 登录 / token                 | 失效后回登录页               |
| 达梦 / 实体同步              | 仅 SELECT；无写语句          |
