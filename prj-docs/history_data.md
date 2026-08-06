# 历史数据查询统计

> 英文名：History Data Query Statistics  
> 模块 ID：`history_data`  
> 所属业务域：配置管理（`/config_management/config`）  
> 页面数：5  
> 上级索引：[README.md](./README.md) · 页面总表：[TOTAL-MODULE.md](./TOTAL-MODULE.md)  
> 来源：前端 routes 权威菜单

## 模块说明

历史数据查询统计（`history_data`）。真实路由为 `parent/path`，**不含 groupId**；源码目录见详档「页面目录」。

## 功能页面

| 页面         | 路径                           | 路由                                                     | 详细文档                                                                                                                                         |
| ------------ | ------------------------------ | -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| 设备索引     | `device_registry_index`        | `/config_management/config/device_registry_index`        | [config_management-config-history_data-device_registry_index.md](./config_management-config-history_data-device_registry_index.md)               |
| 历史数据查询 | `history_query`                | `/config_management/config/history_query`                | [config_management-config-history_data-history_query.md](./config_management-config-history_data-history_query.md)                               |
| 历史曲线查询 | `history_statistics`           | `/config_management/config/history_statistics`           | [config_management-config-history_data-history_statistics.md](./config_management-config-history_data-history_statistics.md)                     |
| 导出模板配置 | `query_template_configuration` | `/config_management/config/query_template_configuration` | [config_management-config-history_data-query_template_configuration.md](./config_management-config-history_data-query_template_configuration.md) |
| 任务管理     | `task_manage`                  | `/config_management/config/task_manage`                  | [config_management-config-history_data-task_manage.md](./config_management-config-history_data-task_manage.md)                                   |

## 操作指引（通用）

1. 登录后进入「配置管理平台」。
2. 打开「配置管理」→「历史数据查询统计」。
3. 按页面按钮维护数据；无权限时在「角色授权 / 菜单管理」分配。

## 代码定位

- `groupId: history_data`
