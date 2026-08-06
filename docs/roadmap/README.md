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

| 阶段   | 焦点                                                                                           |
| ------ | ---------------------------------------------------------------------------------------------- |
| **P0** | 会话运行模式、工具子集注入、对称路径/HITL UX、错误降级                                         |
| **P1** | 运行时 Playbook、显式 Plan、轻量 Subagent、结果卡片、RAG 运营                                  |
| **P2** | 运行时 Hooks/审计、平台 WS 联动闭环、**可观测仪表盘（必须）**、关窗续跑/队列、模型路由、语音等 |

## 可选后续方向

| 方向               | 说明                                                                                                                                                                                                                                                                                                                                                                                     |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Cursor 能力对标    | 见 [cursor-agent-parity.md](./cursor-agent-parity.md)（§3/§7 已与代码对齐）                                                                                                                                                                                                                                                                                                              |
| 工具与结构化卡片   | 消息内结果卡已落地（告警表 / 设备列表 / 导出）。**可做（2026-08-06）**：独立 **Workspace 侧栏**固定展示结构化结果；支持点选行带入追问/触发下一轮（仍走既有 SSE / HITL）。消息内卡片可保留并存。详见 [cursor-agent-parity.md](./cursor-agent-parity.md) §7                                                                                                                                |
| RAG 可运营化       | 设置页知识 CRUD + entity-sync 已有。**可做（2026-08-06）**：entity-sync / 同步水位线与状态写入 **Agent Postgres**（重启可恢复；设置页可读上次成功/失败）；**禁止**在平台达梦写同步标记。详见 [cursor-agent-parity.md](./cursor-agent-parity.md) §7                                                                                                                                       |
| 桌面 ↔ 平台联动    | **可做，换方案（2026-08-06）**：平台侧 **WebSocket** 收智能平台流程 → 平台工具执行 → 结果回传。**client_action 图内回灌（真闭环）可做（同日确认）**：执行结果须回灌 Agent 图（ToolMessage / resume 等），模型可据成败继续决策；禁止长期停留在「仅 audit」。宿主桥 + audit 仅过渡/降级。详见 [cursor-agent-parity.md](./cursor-agent-parity.md) §3.2                                      |
| BPMN 编排 UI       | 未纳入；若开启需单独立项并补契约与验收                                                                                                                                                                                                                                                                                                                                                   |
| Plan 可编辑        | **Won’t do**：平台用户只提目标、不关心执行步骤；不做可编辑 Plan→Build。保留 AI-first 默认、`plan_first` 一键确认门控与步骤条过程可视化（可看/可中止，不可改步骤）                                                                                                                                                                                                                        |
| 领域 / 工具子集    | **可做，须控制度（2026-08-06）**：允许优化 `select_tool_subset` 召回，但**禁止**用关键词/正则替代 AI-first 路径决策；**禁止**堆成第二套 NLU。多意图句须多域并集（例：「有告警就开门」→ alarm∪device），优先不漏用户条件与查询重点；条件判断与调用顺序仍由大模型负责。详见解 [cursor-agent-parity.md](./cursor-agent-parity.md) §3.2                                                      |
| Playbook 增强      | **可做（2026-08-06）**：① **语义检索**——规程向量化（如 Qdrant/Embedding），按用户话术召回 1～N 份注入，替代/补充纯关键词 `triggers`；② **自动评测**——固定用例断言工具调用序列/关键步骤可复现（脚本即可，不必靠人眼）。仍须短索引 + 按需全文，避免 Playbook 堆成第二 prompt 垃圾场。详见 [cursor-agent-parity.md](./cursor-agent-parity.md) §3.2 / §3.3                                   |
| 业务工具扩面       | **方向可做（2026-08-06）**：按平台能力扩展值班 / 门禁 / 配置等（对齐 `prj-docs` / YApi）。**落地形态待讨论**：走 **Platform MCP**（catalog→export→handler→平台 API）还是 Agent 侧 **本地 tool**（`@tool`）。现架构默认与红线倾向 MCP 唯一执行面、Agent 禁业务 `@tool` / 禁 `import platform_mcp`；未拍板前不实现扩面。讨论结论见 [cursor-agent-parity.md](./cursor-agent-parity.md) §3.2 |
| 模型路由升级       | **待评估（2026-08-06）**：现有 Auto + 关键词启发式 light/default 已上线。是否升级为复杂度/代价感知路由 **须先评估**，核心疑问：① 能否提高意图识别准确；② 能否保证快速响应（路由本身是否引入延迟、小模型是否拖慢多步工具链）。评估未通过则不做。详见 [cursor-agent-parity.md](./cursor-agent-parity.md) §3.2                                                                              |
| 写工具强制 confirm | **可做（2026-08-06）**：Agent 层按风险统一强制 confirm→HITL，避免 handler 漏标。**前提**：平台侧增加工具**风险等级配置**（支持用户/运营配置，而非仅在 catalog/代码写死）；Agent/MCP 运行时读取该配置再门控。默认值可来自 catalog，运行时可覆盖。详见 [cursor-agent-parity.md](./cursor-agent-parity.md) §3.2                                                                             |
| 工具 schema 两段式 | **可做（2026-08-06）**：先绑定工具名+短描述，模型选定后再注入完整参数 schema，再调 MCP，以省 token。须保证关键路径不丢工具、与 `select_tool_subset` / resume 指纹兼容。详见 [cursor-agent-parity.md](./cursor-agent-parity.md) §3.2                                                                                                                                                      |
| 多会话 / 关窗续跑  | **可做（2026-08-06）**：在现有「切会话不 abort + notification」之上，增加关窗后续跑与任务队列（服务端持久化执行，重开可看结果）。须闭合 chat/resume/abort 与线程状态。详见 [cursor-agent-parity.md](./cursor-agent-parity.md) §3.2                                                                                                                                                       |
| 可观测仪表盘       | **必须做（2026-08-06）**：对标 LangSmith 思路——运维可观测 + 评估需求功能执行流程是否合理 + 监控各流程执行效率（trace/工具链/延迟/成败/HITL）。落地形态（自建 UI / 对接 LangSmith 等）实施时选定，但能力为硬需求。详见 [cursor-agent-parity.md](./cursor-agent-parity.md) §3.2                                                                                                            |
| 语音 ASR / 声纹    | **可做（2026-08-06）**：ASR 纠错可视化与对话门禁增强；声纹录入/核验/门禁等按 `10-voice-asr` / `11-voiceprint` 继续产品化。详见 [cursor-agent-parity.md](./cursor-agent-parity.md) §3.2                                                                                                                                                                                                   |

## 建议排期（2026-08-06）

排序原则：**影响小 / 实现简单靠前**；**影响大 / 跨系统 / 难靠后**；**待讨论·待评估放最后**。  
不含：Plan 可编辑（Won’t do）、BPMN（未纳入）。

| 批次   | 时机建议     | 项                                                | 难度     | 影响面                    | 备注                                          |
| ------ | ------------ | ------------------------------------------------- | -------- | ------------------------- | --------------------------------------------- |
| **W0** | 第 1 迭代    | RAG / entity-sync **状态持久化**                  | 低       | 小                        | ✅ 水位线/成败→Agent Postgres；禁达梦写标记   |
| **W0** | 第 1 迭代    | Playbook **自动评测**（脚本用例）                 | 低       | 小                        | ✅ `scripts/eval_playbook.py`；不改运行时主链 |
| **W0** | 第 1 迭代    | 领域 / 工具子集 **控制度优化**                    | 低～中   | 小～中                    | ✅ 多域并集 + 条件句防漏；禁堆词 NLU          |
| **W1** | 第 2 迭代    | **Workspace 侧栏**（结果卡）                      | 中       | 中（桌面 UI）             | 点选追问；与消息内卡片并存                    |
| **W1** | 第 2～3 迭代 | Playbook **语义检索**                             | 中       | 中                        | Embedding + 限份注入                          |
| **W1** | 第 2～3 迭代 | 工具 schema **两段式**                            | 中       | 中（Agent 绑工具）        | 省 token；与 subset/resume 兼容               |
| **W2** | 第 3～4 迭代 | **可观测仪表盘**（**必须做**）                    | 中～高   | 中～大                    | 对标 LangSmith；宜相对靠前以便评估后续项      |
| **W2** | 第 3～4 迭代 | 写工具统一强制 confirm + **平台风险等级配置**     | 中       | 中（门控+平台配置）       | 平台可配风险是前提；可与仪表盘并行            |
| **W3** | 第 4～5 迭代 | 语音 ASR / 声纹增强                               | 中～高   | 中（语音链路）            | 可与 W2/W4 部分并行；按 `10`/`11`             |
| **W3** | 第 5～6 迭代 | 多会话 / **关窗续跑** / **任务队列**              | 高       | 大（会话生命周期）        | 依赖状态持久化与对称路径硬化                  |
| **W4** | 第 6～8 迭代 | **client_action 图内回灌** + **平台 WS 联动闭环** | 高       | 大（跨智能平台↔业务平台） | 须与平台共建协议；宿主桥仅过渡                |
| **W5** | 讨论拍板后   | **业务工具扩面**（值班/门禁/配置…）               | 视域而定 | 大（能力面）              | **MCP vs 本地 tool 未拍板前不编码**           |
| **W6** | 最后         | **模型路由升级**                                  | —        | —                         | **待评估**；未证明「更准+更快」则不做         |

### 批次依赖（简图）

```text
W0 持久化/评测/子集控制度
  → W1 侧栏 / Playbook 语义 / 两段式 schema
    → W2 可观测仪表盘（必须）∥ 风险可配 + 统一 confirm
      → W3 语音 ∥ 关窗续跑/队列
        → W4 WS + 图内回灌真闭环
          → W5 业务扩面（先拍板 MCP/tool）
            → W6 模型路由评估（最后）
```

### 并行建议

- **可观测（W2）** 与 **风险配置+confirm（W2）**、**语音（W3）** 可部分并行（不同模块）。
- **W4** 与平台排期强绑定，智能侧可先做图内回灌契约草案，再等 WS 联调。
- **W5** 仅开会拍板即可提前插入任意批次之间；未拍板不得开工实现。
