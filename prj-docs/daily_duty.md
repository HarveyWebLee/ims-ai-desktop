# 日常值班

> 英文名：Daily Duty  
> 模块 ID：`daily_duty`  
> 所属业务域：阵地维护管理（`/config_management/positional_management`）  
> 页面数：6  
> 上级索引：[README.md](./README.md) · 页面总表：[TOTAL-MODULE.md](./TOTAL-MODULE.md)  
> 来源：前端 routes 权威菜单

## 模块说明

日常值班（`daily_duty`）。真实路由为 `parent/path`，**不含 groupId**；源码目录见详档「页面目录」。

## 功能页面

| 页面         | 路径                  | 路由                                                           | 详细文档                                                                                                                                                 |
| ------------ | --------------------- | -------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 值班信息     | `duty_information`    | `/config_management/positional_management/duty_information`    | [config_management-positional_management-daily_duty-duty_information.md](./config_management-positional_management-daily_duty-duty_information.md)       |
| 值班日志     | `duty_logs`           | `/config_management/positional_management/duty_logs`           | [config_management-positional_management-daily_duty-duty_logs.md](./config_management-positional_management-daily_duty-duty_logs.md)                     |
| 值班计划     | `duty_plan`           | `/config_management/positional_management/duty_plan`           | [config_management-positional_management-daily_duty-duty_plan.md](./config_management-positional_management-daily_duty-duty_plan.md)                     |
| 值班岗位设置 | `duty_setting`        | `/config_management/positional_management/duty_setting`        | [config_management-positional_management-daily_duty-duty_setting.md](./config_management-positional_management-daily_duty-duty_setting.md)               |
| 阵地出入审批 | `entry_exit_approval` | `/config_management/positional_management/entry_exit_approval` | [config_management-positional_management-daily_duty-entry_exit_approval.md](./config_management-positional_management-daily_duty-entry_exit_approval.md) |
| 交接班记录   | `week_handover`       | `/config_management/positional_management/week_handover`       | [config_management-positional_management-daily_duty-week_handover.md](./config_management-positional_management-daily_duty-week_handover.md)             |

## 操作指引（通用）

1. 登录后进入「配置管理平台」。
2. 打开「阵地维护管理」→「日常值班」。
3. 按页面按钮维护数据；无权限时在「角色授权 / 菜单管理」分配。

## 代码定位

- `groupId: daily_duty`
