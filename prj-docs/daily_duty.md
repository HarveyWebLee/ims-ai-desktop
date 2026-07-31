# 日常值班

> 英文名：Daily Duty  
> 模块 ID：`daily_duty`  
> 所属业务域：阵地维护管理（`/config_management/positional_management`）  
> 来源：平台功能模块知识库（本仓 `prj-docs`）

## 模块说明

值班信息/计划/日志、交接班记录、值班岗位设置与阵地出入审批。

## 适用场景

阵地设施、值班、人员、巡检、保养、工具备件、故障维修与计量移交等日常保障场景。

## 功能页面

| 页面         | 路径                  | 路由                                                           | 说明                 |
| ------------ | --------------------- | -------------------------------------------------------------- | -------------------- |
| 值班信息     | `duty_information`    | `/config_management/positional_management/duty_information`    | 阵地值班信息。       |
| 值班计划     | `duty_plan`           | `/config_management/positional_management/duty_plan`           | 排班与值班计划。     |
| 值班日志     | `duty_logs`           | `/config_management/positional_management/duty_logs`           | 值班日志填写与查询。 |
| 交接班记录   | `week_handover`       | `/config_management/positional_management/week_handover`       | 交接班记录。         |
| 值班岗位设置 | `duty_setting`        | `/config_management/positional_management/duty_setting`        | 值班岗位设置。       |
| 阵地出入审批 | `entry_exit_approval` | `/config_management/positional_management/entry_exit_approval` | 阵地人员出入审批。   |

## 操作指引（通用）

1. 登录综合信息管理平台，从门户进入「配置管理平台」。
2. 打开左侧「阵地维护管理」→「日常值班」。
3. 在列表页按条件查询；通过新增/编辑/删除维护数据（具体按钮以页面为准）。
4. 若页面含树形筛选（区域/组织/类别），先选节点再操作右侧列表。
5. 无菜单权限时，请管理员在「角色授权 / 菜单管理」中分配。

## 关联依赖

依赖值班岗位设置；出入审批与人员信息联动。

## 常见问题

- **看不到本模块菜单**：检查账号角色是否授权；超级管理员可在「菜单管理 / 角色授权 / 场景管理」配置。
- **列表无数据**：确认筛选条件、所属区域/组织节点，以及后端服务与数据权限范围。
- **无法保存**：检查必填项、字典引用是否存在，以及是否具备写权限。

## 代码定位

- 功能分组：`groupId: daily_duty`
- 对应平台配置管理功能页面
