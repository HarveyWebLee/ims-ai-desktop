# 提示词管理说明

## 目录

| 文件                  | 用途                                                                      |
| --------------------- | ------------------------------------------------------------------------- |
| `system.md`           | 主 Agent 身份与核心原则（精简）                                           |
| `intent_and_tools.md` | 意图映射、时间约定、正反例（参数细节见 tool Schema）                      |
| `response_style.md`   | 面向使用者的总结回复结构（原 `summarize.md`，注入主 Agent system prompt） |
| `llm_plan.md`         | D1 LLM 显式任务规划（原 `plan.md` 规则已合并）                            |
| `llm_plan_params.md`  | D1 规划步骤参数补全                                                       |
| `chat_direct.md`      | 纯对话短路（Phase C1）                                                    |
| `asr_correct.md`      | 语音 ASR 后基于知识库术语纠错（transcribe 前置）                          |

## 运行时组装

`app/services/prompt_assembly.py` 按序拼接：

1. `system.md` + `intent_and_tools.md` + `response_style.md`
2. 已注册工具 ↔ 平台 API 对照表（**读取 catalog.json**，与 `tool-catalog.ts` 一致）
3. 告警域 API 摘要（来自 `platform_api_index.json`，非全量 swagger）
4. 当前时间 + 导航规范 + 常用路由（来自 `navigation_routes.json`）

`llm_task_planner.py` 单独加载 `llm_plan.md`（多步 Plan，不经主 system prompt）。

单次请求的页面路径与近期消息由 `build_llm_user_message()` 注入**用户消息**，不重复写入 Agent 级 system prompt。

## 编写规范

1. **使用者视角**：站在值班员/管理员一侧，禁止研发术语
2. **不重复 Schema**：工具参数以 LangChain 注册的 JSON Schema 为准，prompt 只写语义与边界
3. **与 tool-catalog 一致**：新增工具时更新 `tool-catalog.ts` 并 `export_catalog.py`，绑定表自动同步

## 变更记录

| 版本 | 日期       | 说明                                                                    |
| ---- | ---------- | ----------------------------------------------------------------------- |
| v0.1 | 2026-07-01 | Phase 0 初始 system/plan/summarize                                      |
| v0.2 | 2026-07-02 | 精简 intent；注入工具/API 摘要；Phase A 编排抽离                        |
| v0.3 | 2026-07-03 | plan→llm_plan、summarize→response_style；catalog 驱动绑定表与 preflight |
