# 运行时 Playbook（Skills 等价）

按用户意图匹配后注入本轮 `llm_user_message`，引导多步流程（告警处置、批量导出等）。  
不进入 system prompt，避免打散 `create_agent` 缓存。

## 文件格式

每个 `.md` 文件：YAML 风格 frontmatter + Markdown 正文。

```markdown
---
id: alarm-dispose
title: 告警处置
version: "1.0"
priority: 100
triggers:
  - 告警
  - 处理告警
domains:
  - alarm
---

## 目标

...
```

| 字段       | 说明                                    |
| ---------- | --------------------------------------- |
| `id`       | 稳定标识（必填）                        |
| `title`    | 展示名                                  |
| `version`  | 语义版本字符串                          |
| `priority` | 同分时优先（越大越优先）；默认 0        |
| `triggers` | 关键词列表，命中用户句则计分            |
| `domains`  | 可选；与工具子集 domains 对齐，作弱加权 |

## 运营

- 改 Markdown 后**无需发版重编译**
- 默认开启目录监听（`AGENT_PLAYBOOK_WATCH=true`）：保存 `.md` 后自动 `reload_playbooks()` 刷新内存缓存，**不重启** Agent 进程
- 也可手动：进程重启，或进程内调用 `reload_playbooks()`
- 关闭 Playbook：`AGENT_PLAYBOOK_ENABLED=false`
- 关闭监听：`AGENT_PLAYBOOK_WATCH=false`
- 自定义目录：`AGENT_PLAYBOOK_DIR=/path/to/playbooks`

## 注入点

`app/graph/context.py` → `assemble_context`（与被动 RAG 并列，失败不阻断对话）
