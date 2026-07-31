---
name: architecture-refactor-compat
description: >-
  在不破坏既有桌面/Agent/MCP 主链的前提下做结构性重构。
  在用户要求删冗余层、统一入口、迁路径或优化架构时使用。
---

# 结构性重构（兼容优先）

## 1) 重构前

- 列出旧入口与新入口（调用方清单）
- 识别测试 patch、脚本、文档路径依赖
- 标记必须保留的兼容点

## 2) 手法

1. 内聚迁移到目标模块（注意 `services/` 与 `apps/desktop` 边界；共享逻辑进 `platform-contracts`/`contracts`，工具 handler 留 MCP `runtime/tools`）
2. 更新全部 import / 脚本路径（Agent **不得**再 `import platform_mcp`）
3. 可选：旧入口仅转发并标注 deprecate
4. 确认无引用后再删除；守卫测试：`tests/test_no_platform_mcp_import.py`

## 3) 必测

- Agent：`uv run check lint && uv run check typecheck`（及必要 pytest；或根目录 `pnpm check`）
- 桌面：M1 主路径手测
- 全局检索失效路径与断裂 import

## 4) 风险模板

- 可能影响：导入路径、联调脚本、Cursor rules/skills 引用
- 缓解：grep + 测试 + 文档同步更新
