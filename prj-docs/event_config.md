# 事件配置

> 英文名：Event Config  
> 模块 ID：`event_config`  
> 所属业务域：配置管理（`/config_management/config`）  
> 页面数：5  
> 上级索引：[README.md](./README.md) · 页面总表：[TOTAL-MODULE.md](./TOTAL-MODULE.md)  
> 来源：前端 routes 权威菜单

## 模块说明

事件配置（`event_config`）。真实路由为 `parent/path`，**不含 groupId**；源码目录见详档「页面目录」。

## 功能页面

| 页面           | 路径                     | 路由                                               | 详细文档                                                                                                                             |
| -------------- | ------------------------ | -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| 周期事件配置   | `cycle_event_config`     | `/config_management/config/cycle_event_config`     | [config_management-config-event_config-cycle_event_config.md](./config_management-config-event_config-cycle_event_config.md)         |
| 事件执行记录   | `event_execution_record` | `/config_management/config/event_execution_record` | [config_management-config-event_config-event_execution_record.md](./config_management-config-event_config-event_execution_record.md) |
| 事件流配置     | `event_flow_config`      | `/config_management/config/event_flow_config`      | [config_management-config-event_config-event_flow_config.md](./config_management-config-event_config-event_flow_config.md)           |
| 事件联动规则   | `event_link_rule`        | `/config_management/config/event_link_rule`        | [config_management-config-event_config-event_link_rule.md](./config_management-config-event_config-event_link_rule.md)               |
| 事件联动记录表 | `event_rule_record`      | `/config_management/config/event_rule_record`      | [config_management-config-event_config-event_rule_record.md](./config_management-config-event_config-event_rule_record.md)           |

## 操作指引（通用）

1. 登录后进入「配置管理平台」。
2. 打开「配置管理」→「事件配置」。
3. 按页面按钮维护数据；无权限时在「角色授权 / 菜单管理」分配。

## 代码定位

- `groupId: event_config`
