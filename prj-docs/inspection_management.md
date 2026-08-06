# 阵地巡检管理

> 英文名：Position Inspection Management  
> 模块 ID：`inspection_management`  
> 所属业务域：阵地维护管理（`/config_management/positional_management`）  
> 页面数：5  
> 上级索引：[README.md](./README.md) · 页面总表：[TOTAL-MODULE.md](./TOTAL-MODULE.md)  
> 来源：前端 routes 权威菜单

## 模块说明

阵地巡检管理（`inspection_management`）。真实路由为 `parent/path`，**不含 groupId**；源码目录见详档「页面目录」。

## 功能页面

| 页面         | 路径                             | 路由                                                                      | 详细文档                                                                                                                                                                                             |
| ------------ | -------------------------------- | ------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 巡检点位管理 | `inspection_point_management`    | `/config_management/positional_management/inspection_point_management`    | [config_management-positional_management-inspection_management-inspection_point_management.md](./config_management-positional_management-inspection_management-inspection_point_management.md)       |
| 巡检项目管理 | `inspection_project_management`  | `/config_management/positional_management/inspection_project_management`  | [config_management-positional_management-inspection_management-inspection_project_management.md](./config_management-positional_management-inspection_management-inspection_project_management.md)   |
| 操作记录     | `inspection_task_operate_record` | `/config_management/positional_management/inspection_task_operate_record` | [config_management-positional_management-inspection_management-inspection_task_operate_record.md](./config_management-positional_management-inspection_management-inspection_task_operate_record.md) |
| 巡检方案管理 | `routine_inspection`             | `/config_management/positional_management/routine_inspection`             | [config_management-positional_management-inspection_management-routine_inspection.md](./config_management-positional_management-inspection_management-routine_inspection.md)                         |
| 巡查任务管理 | `routine_inspection_task`        | `/config_management/positional_management/routine_inspection_task`        | [config_management-positional_management-inspection_management-routine_inspection_task.md](./config_management-positional_management-inspection_management-routine_inspection_task.md)               |

## 操作指引（通用）

1. 登录后进入「配置管理平台」。
2. 打开「阵地维护管理」→「阵地巡检管理」。
3. 按页面按钮维护数据；无权限时在「角色授权 / 菜单管理」分配。

## 代码定位

- `groupId: inspection_management`
