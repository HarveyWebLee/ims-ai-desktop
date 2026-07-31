# 设施设备管理

> 英文名：Facilities and Equipment Management  
> 模块 ID：`facilities_management`  
> 所属业务域：阵地维护管理（`/config_management/positional_management`）  
> 来源：平台功能模块知识库（本仓 `prj-docs`）

## 模块说明

属性字典、类别、安装部位、设施台账、质量统计、动用使用与交接管理。

## 适用场景

阵地设施、值班、人员、巡检、保养、工具备件、故障维修与计量移交等日常保障场景。

## 功能页面

| 页面     | 路径                          | 路由                                                                   | 说明                             |
| -------- | ----------------------------- | ---------------------------------------------------------------------- | -------------------------------- |
| 属性字典 | `attribute_dictionary`        | `/config_management/positional_management/attribute_dictionary`        | 设施设备属性字典，定义设施字段。 |
| 类别管理 | `category_management`         | `/config_management/positional_management/category_management`         | 设施/设备类别管理。              |
| 安装部位 | `install_position_management` | `/config_management/positional_management/install_position_management` | 安装部位主数据。                 |
| 设施管理 | `facility_management`         | `/config_management/positional_management/facility_management`         | 设施台账管理。                   |
| 质量统计 | `quality_statistics`          | `/config_management/positional_management/quality_statistics`          | 设施质量统计。                   |
| 动用使用 | `usage`                       | `/config_management/positional_management/usage`                       | 设施动用使用登记。               |
| 交接管理 | `handover_management`         | `/config_management/positional_management/handover_management`         | 设施交接管理。                   |

## 操作指引（通用）

1. 登录综合信息管理平台，从门户进入「配置管理平台」。
2. 打开左侧「阵地维护管理」→「设施设备管理」。
3. 在列表页按条件查询；通过新增/编辑/删除维护数据（具体按钮以页面为准）。
4. 若页面含树形筛选（区域/组织/类别），先选节点再操作右侧列表。
5. 无菜单权限时，请管理员在「角色授权 / 菜单管理」中分配。

## 关联依赖

属性字典与类别是设施台账的前置主数据。

## 常见问题

- **看不到本模块菜单**：检查账号角色是否授权；超级管理员可在「菜单管理 / 角色授权 / 场景管理」配置。
- **列表无数据**：确认筛选条件、所属区域/组织节点，以及后端服务与数据权限范围。
- **无法保存**：检查必填项、字典引用是否存在，以及是否具备写权限。

## 代码定位

- 功能分组：`groupId: facilities_management`
- 对应平台配置管理功能页面
