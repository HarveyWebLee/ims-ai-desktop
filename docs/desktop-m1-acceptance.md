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
6. **P2-4 多会话并行（最小切片）**：会话 A 流式中切到 B 发消息 → A 后台继续；完成后 notification；切回 A 可见完整气泡；Stop 仅中止当前会话
7. MCP 不可达时：明确「MCP 不可用」类错误提示（非 unknown）
8. `curl -s localhost:8008/health` 正常；MCP `:8010` 可达
9. Playbook（可选）：发「处理未确认告警」/「导出告警」→ Agent 按规程查询/导出（步骤可复现；改 `app/playbooks` 后重启生效）
10. 先计划：打开「先计划」开关 → 发「查近三天告警然后导出」→ 出现 plan_confirm → 批准后才执行导出
11. Subagent 检索（可选）：问产品/流程类知识 → `retrieve_knowledge` 工具结果为摘要（非大段原文），主回复仍连贯
12. 结果卡片：`query_alarms` 查表；`query_devices` 设备列表（点行可让助手查详情）；`download_file` 导出结果卡（含取消态）
13. RAG 运营（可选）：设置 → 知识与术语 → 文档规程（统计/展开预览/上传/下载）；实体术语（统计/试检索设备变量/同步）
14. 运行时 Hooks（可选）：`.env` 设 `AGENT_TOOL_HOOK_DENY_TOOLS=download_file` → 对话触发导出被拒；设置 → 审计可见「Hooks 拦截」；清名单后恢复
15. client_action 闭环（可选）：`localStorage.setItem('ims_ai_mock_platform_host','1')` → 发「打开设施管理」→ toast 模拟导航成功；设置 → 审计可见「Client 执行回执」；清 mock 后恢复跳过降级
16. 模型路由（可选）：侧栏选「自动」→ 轻任务走轻量模型、导出/处置走默认通义 3.5 35B；目录仅含实测可用模型（已删除通义 8B / 32B 与无额度的 3.7 Plus / Plus 2025-07-28）
17. **可观测仪表盘**：设置 → 可观测 → 可见运行数/成功率/延迟/HITL/工具失败率；列表**按会话分组**展开；点某 run 可下钻**本轮过程时间线**（用户输入 → 被动 RAG → LLM 入参 → MCP/RAG 工具参数与结果 → 助手回复 → 结束）；chat → HITL 批准/拒绝 → abort 后刷新可见对应状态（当前用户数据；**新对话后**才有完整 LLM/RAG 时间线，旧 run 可能仅有工具事件）

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
