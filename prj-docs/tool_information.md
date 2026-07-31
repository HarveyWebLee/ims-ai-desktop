# 工具资料

> 英文名：Tools and Materials  
> 模块 ID：`tool_information`  
> 所属业务域：阵地维护管理（`/config_management/positional_management`）  
> 来源：平台功能模块知识库（本仓 `prj-docs`）

## 模块说明

工具类型、存放位置、工具与资料台账管理。

## 适用场景

阵地设施、值班、人员、巡检、保养、工具备件、故障维修与计量移交等日常保障场景。

## 功能页面

| 页面     | 路径                          | 路由                                                                   | 说明                |
| -------- | ----------------------------- | ---------------------------------------------------------------------- | ------------------- |
| 工具类型 | `tool_type_management`        | `/config_management/positional_management/tool_type_management`        | 工具类型。          |
| 存放位置 | `storage_position_management` | `/config_management/positional_management/storage_position_management` | 工具/资料存放位置。 |
| 工具管理 | `tool_management`             | `/config_management/positional_management/tool_management`             | 工具台账。          |
| 资料管理 | `material_management`         | `/config_management/positional_management/material_management`         | 资料台账。          |

## 操作指引（通用）

1. 登录综合信息管理平台，从门户进入「配置管理平台」。
2. 打开左侧「阵地维护管理」→「工具资料」。
3. 在列表页按条件查询；通过新增/编辑/删除维护数据（具体按钮以页面为准）。
4. 若页面含树形筛选（区域/组织/类别），先选节点再操作右侧列表。
5. 无菜单权限时，请管理员在「角色授权 / 菜单管理」中分配。

## 关联依赖

工具类型与存放位置是工具/资料台账前置数据。

## 常见问题

- **看不到本模块菜单**：检查账号角色是否授权；超级管理员可在「菜单管理 / 角色授权 / 场景管理」配置。
- **列表无数据**：确认筛选条件、所属区域/组织节点，以及后端服务与数据权限范围。
- **无法保存**：检查必填项、字典引用是否存在，以及是否具备写权限。

## 代码定位

- 功能分组：`groupId: tool_information`
- 对应平台配置管理功能页面
