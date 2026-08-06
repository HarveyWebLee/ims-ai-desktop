# 日志管理

> 英文名：Log Management  
> 模块 ID：`log`  
> 所属业务域：系统管理（`/config_management/system`）  
> 页面数：5  
> 上级索引：[README.md](./README.md) · 页面总表：[TOTAL-MODULE.md](./TOTAL-MODULE.md)  
> 来源：前端 routes 权威菜单

## 模块说明

日志管理（`log`）。真实路由为 `parent/path`，**不含 groupId**；源码目录见详档「页面目录」。

## 功能页面

| 页面         | 路径                       | 路由                                                 | 详细文档                                                                                                               |
| ------------ | -------------------------- | ---------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| 业务应用日志 | `business_application_log` | `/config_management/system/business_application_log` | [config_management-system-log-business_application_log.md](./config_management-system-log-business_application_log.md) |
| 日志审计     | `log_audit`                | `/config_management/system/log_audit`                | [config_management-system-log-log_audit.md](./config_management-system-log-log_audit.md)                               |
| 日志策略配置 | `log_policy_config`        | `/config_management/system/log_policy_config`        | [config_management-system-log-log_policy_config.md](./config_management-system-log-log_policy_config.md)               |
| 系统运行日志 | `system_runtime_log`       | `/config_management/system/system_runtime_log`       | [config_management-system-log-system_runtime_log.md](./config_management-system-log-system_runtime_log.md)             |
| 用户行为日志 | `user_behavior_log`        | `/config_management/system/user_behavior_log`        | [config_management-system-log-user_behavior_log.md](./config_management-system-log-user_behavior_log.md)               |

## 操作指引（通用）

1. 登录后进入「配置管理平台」。
2. 打开「系统管理」→「日志管理」。
3. 按页面按钮维护数据；无权限时在「角色授权 / 菜单管理」分配。

## 代码定位

- `groupId: log`
