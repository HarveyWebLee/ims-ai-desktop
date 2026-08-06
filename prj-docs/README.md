# 综合信息平台 — 项目知识库索引

> 菜单与路由以平台前端 routes 为准。  
> 真实路由：`{parent}/{path}`（不含 groupId）。源码目录：`src/pages` + `filePath`。

## 文档层级

```text
README.md
├── {groupId}.md
│   └── config_management-*.md
└── TOTAL-MODULE.md
```

## 业务域与功能模块

### 配置管理（`/config_management/config`）

| 功能模块         | 文件                                                       | 页面数 |
| ---------------- | ---------------------------------------------------------- | ------ |
| 事件配置         | [event_config.md](./event_config.md)                       | 5      |
| 历史数据查询统计 | [history_data.md](./history_data.md)                       | 5      |
| 周界防区设定     | [perimeter_setting.md](./perimeter_setting.md)             | 4      |
| 报警查询统计     | [alarm_query_statistics.md](./alarm_query_statistics.md)   | 2      |
| 数采服务器       | [data_acquisition_server.md](./data_acquisition_server.md) | 3      |
| 监控设备         | [monitor_equipment.md](./monitor_equipment.md)             | 4      |
| 系统监控         | [system_monitor.md](./system_monitor.md)                   | 1      |
| 设备变量         | [device_variable.md](./device_variable.md)                 | 4      |

### 系统管理（`/config_management/system`）

| 功能模块       | 文件                                               | 页面数 |
| -------------- | -------------------------------------------------- | ------ |
| 信息发布       | [information_release.md](./information_release.md) | 3      |
| 基础数据       | [basedata.md](./basedata.md)                       | 8      |
| 字典表         | [dic_table.md](./dic_table.md)                     | 11     |
| 日志管理       | [log.md](./log.md)                                 | 5      |
| 用户及参数管理 | [user.md](./user.md)                               | 8      |
| 系统运维       | [system_devops.md](./system_devops.md)             | 2      |
| 门禁系统       | [door_access_system.md](./door_access_system.md)   | 8      |

### 阵地维护管理（`/config_management/positional_management`）

| 功能模块     | 文件                                                                               | 页面数 |
| ------------ | ---------------------------------------------------------------------------------- | ------ |
| 备品备件管理 | [spare_parts_management.md](./spare_parts_management.md)                           | 1      |
| 工具资料     | [tool_information.md](./tool_information.md)                                       | 4      |
| 故障维修管理 | [fault_repair_management.md](./fault_repair_management.md)                         | 2      |
| 日常值班     | [daily_duty.md](./daily_duty.md)                                                   | 6      |
| 物资移交管理 | [transfer_management_service.md](./transfer_management_service.md)                 | 1      |
| 维护保养管理 | [maintenance_management.md](./maintenance_management.md)                           | 3      |
| 计量校验管理 | [measurement_verification_management.md](./measurement_verification_management.md) | 1      |
| 设施设备管理 | [facilities_management.md](./facilities_management.md)                             | 7      |
| 阵地人员管理 | [staff_management.md](./staff_management.md)                                       | 1      |
| 阵地巡检管理 | [inspection_management.md](./inspection_management.md)                             | 5      |

### 门户与其它

见 [TOTAL-MODULE.md](./TOTAL-MODULE.md)。

## 入库

```bash
bash scripts/kb.sh --dir ./prj-docs --ext .md
```

## 维护约定

1. 以前端 `groupId` / `path` / `parent` / `filePath` 为准同步本目录。
2. 未挂菜单的页面不写入模块索引。
3. 页面详档文件名与 `filePath` 段一致。
