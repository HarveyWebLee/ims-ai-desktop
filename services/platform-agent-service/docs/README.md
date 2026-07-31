# platform-agent-service 文档索引

本目录存放 **Agent 服务自身** 的运维与学习文档。架构基准仍以 monorepo 的 [`docs/architecture/`](../../docs/architecture/00-overview.md) 为准。

| 文档                                             | 用途                                     |
| ------------------------------------------------ | ---------------------------------------- |
| [code-reading-guide.md](./code-reading-guide.md) | **代码学习阅读路径**：按调用链分层读源码 |
| [qdrant-deployment.md](./qdrant-deployment.md)   | Qdrant 部署、入库与检索                  |

## 推荐阅读顺序（新人）

1. [`../README.md`](../README.md) — 启动、依赖、健康检查
2. [`../../docs/architecture/00-overview.md`](../../docs/architecture/00-overview.md) — 系统目标与零兼容原则
3. [`../../docs/architecture/03-agent-runtime.md`](../../docs/architecture/03-agent-runtime.md) — 父图 / HITL / SSE
4. **本目录** [code-reading-guide.md](./code-reading-guide.md) — 对着源码走一遍主链
5. 需要改工具时：[`../../docs/architecture/02-mcp-platform-server.md`](../../docs/architecture/02-mcp-platform-server.md)
6. 需要改契约时：[`../../docs/architecture/06-contracts.md`](../../docs/architecture/06-contracts.md)

## 相关规范（非本目录）

| 位置                                                                                                   | 说明                     |
| ------------------------------------------------------------------------------------------------------ | ------------------------ |
| [`../../.cursor/rules/agent-architecture-first.mdc`](../../.cursor/rules/agent-architecture-first.mdc) | 改功能时的架构优先顺序   |
| [`../../.cursor/rules/feature-change-integrity.mdc`](../../.cursor/rules/feature-change-integrity.mdc) | Agent 影响面与回归完整性 |
| [`../../.cursor/rules/ai-dev-quality-gates.mdc`](../../.cursor/rules/ai-dev-quality-gates.mdc)         | 改前影响面 / 改后门禁    |
| [`../../docs/desktop-m1-acceptance.md`](../../docs/desktop-m1-acceptance.md)                           | 桌面端手工验收           |
