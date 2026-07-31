# 综合信息平台 — 项目知识库索引

> 本目录知识库按平台业务功能分组（`group` / `groupId`）拆分，
> 供 Agent RAG 检索与业务问答使用。一个功能模块对应一个 Markdown 文件。

## 平台概述

综合信息管理平台以**配置管理**为核心，覆盖系统管理、设备监控、事件联动、周界安防、
报警与历史数据、门禁与信息发布，以及阵地设施/值班/巡检/保养/维修等业务域。

入口路径：

- 门户导航：`/overview`
- 配置管理平台：`/config_management`
- 登录页：`/login`

## 业务域与功能模块

### 配置管理

| 功能模块         | 文件                                                       | 页面数 |
| ---------------- | ---------------------------------------------------------- | ------ |
| 数采服务器       | [data_acquisition_server.md](./data_acquisition_server.md) | 3      |
| 监控设备         | [monitor_equipment.md](./monitor_equipment.md)             | 3      |
| 设备变量         | [device_variable.md](./device_variable.md)                 | 4      |
| 事件配置         | [event_config.md](./event_config.md)                       | 6      |
| 周界防区设定     | [perimeter_setting.md](./perimeter_setting.md)             | 4      |
| 系统监控         | [system_monitor.md](./system_monitor.md)                   | 1      |
| 报警查询统计     | [alarm_query_statistics.md](./alarm_query_statistics.md)   | 2      |
| 历史数据查询统计 | [history_data.md](./history_data.md)                       | 6      |

### 系统管理

| 功能模块       | 文件                                               | 页面数 |
| -------------- | -------------------------------------------------- | ------ |
| 用户及参数管理 | [user.md](./user.md)                               | 9      |
| 日志管理       | [log.md](./log.md)                                 | 8      |
| 基础数据       | [basedata.md](./basedata.md)                       | 8      |
| 系统运维       | [system_devops.md](./system_devops.md)             | 2      |
| 字典表         | [dic_table.md](./dic_table.md)                     | 11     |
| 门禁系统       | [door_access_system.md](./door_access_system.md)   | 8      |
| 信息发布       | [information_release.md](./information_release.md) | 3      |

### 阵地维护管理

| 功能模块     | 文件                                                                               | 页面数 |
| ------------ | ---------------------------------------------------------------------------------- | ------ |
| 设施设备管理 | [facilities_management.md](./facilities_management.md)                             | 7      |
| 日常值班     | [daily_duty.md](./daily_duty.md)                                                   | 6      |
| 阵地人员管理 | [staff_management.md](./staff_management.md)                                       | 1      |
| 阵地巡检管理 | [inspection_management.md](./inspection_management.md)                             | 5      |
| 维护保养管理 | [maintenance_management.md](./maintenance_management.md)                           | 3      |
| 工具资料     | [tool_information.md](./tool_information.md)                                       | 4      |
| 备品备件管理 | [spare_parts_management.md](./spare_parts_management.md)                           | 1      |
| 故障维修管理 | [fault_repair_management.md](./fault_repair_management.md)                         | 2      |
| 计量校验管理 | [measurement_verification_management.md](./measurement_verification_management.md) | 1      |
| 物资移交管理 | [transfer_management_service.md](./transfer_management_service.md)                 | 1      |

## 入库说明

本目录仅放功能模块 Markdown；**不要**把 `swaggerApi.json` / `platform_api_*.json` 等平台 API 数据拷入此处（它们已在 `platform-agent-service/app/data/`）。

```bash
# 推荐：只入库 .md
bash scripts/kb.sh --dir ./prj-docs --ext .md
```

或：

```bash
cd platform-agent-service
uv run kb --dir ../prj-docs --ext .md
```

## 维护约定

1. 功能模块边界以 `routes.tsx` 的 `meta.groupId` 为准；增删菜单分组时同步增删本目录文件。
2. 仅记录当前启用路由（已注释菜单不写入）。
3. 文件命名：`{groupId}.md`。
