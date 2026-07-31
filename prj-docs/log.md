# 日志管理

> 英文名：Log Management  
> 模块 ID：`log`  
> 所属业务域：系统管理（`/config_management/system`）  
> 来源：平台功能模块知识库（本仓 `prj-docs`）

## 模块说明

系统运行、业务应用、用户行为等日志查询，以及日志审计与策略配置。

## 适用场景

账号权限、基础主数据、日志审计、门禁业务与信息发布等系统级管理场景。

## 功能页面

| 页面                     | 路径                       | 路由                                                 | 说明                           |
| ------------------------ | -------------------------- | ---------------------------------------------------- | ------------------------------ |
| 系统运行日志             | `system_runtime_log`       | `/config_management/system/system_runtime_log`       | 查询系统运行日志。             |
| 业务应用日志             | `business_application_log` | `/config_management/system/business_application_log` | 查询业务应用日志。             |
| 用户行为日志             | `user_behavior_log`        | `/config_management/system/user_behavior_log`        | 查询用户行为审计日志。         |
| 日志审计                 | `log_audit`                | `/config_management/system/log_audit`                | 日志审计工作台。               |
| 日志策略配置             | `log_policy_config`        | `/config_management/system/log_policy_config`        | 配置日志采集与保留策略。       |
| 系统访问日志（菜单隐藏） | `system_access`            | `/config_management/system/system_access`            | 系统访问日志（菜单默认隐藏）。 |
| 系统操作日志（菜单隐藏） | `system_operation`         | `/config_management/system/system_operation`         | 系统操作日志（菜单默认隐藏）。 |
| 设备操作日志（菜单隐藏） | `equipment_operation`      | `/config_management/system/equipment_operation`      | 设备操作日志（菜单默认隐藏）。 |

## 操作指引（通用）

1. 登录综合信息管理平台，从门户进入「配置管理平台」。
2. 打开左侧「系统管理」→「日志管理」。
3. 在列表页按条件查询；通过新增/编辑/删除维护数据（具体按钮以页面为准）。
4. 若页面含树形筛选（区域/组织/类别），先选节点再操作右侧列表。
5. 无菜单权限时，请管理员在「角色授权 / 菜单管理」中分配。

## 关联依赖

各业务操作会产生用户行为/业务日志，供审计与排障。

## 常见问题

- **看不到本模块菜单**：检查账号角色是否授权；超级管理员可在「菜单管理 / 角色授权 / 场景管理」配置。
- **列表无数据**：确认筛选条件、所属区域/组织节点，以及后端服务与数据权限范围。
- **无法保存**：检查必填项、字典引用是否存在，以及是否具备写权限。

## 代码定位

- 功能分组：`groupId: log`
- 对应平台配置管理功能页面
