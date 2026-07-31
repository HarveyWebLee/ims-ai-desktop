# 用户及参数管理

> 英文名：User and Parameter Management  
> 模块 ID：`user`  
> 所属业务域：系统管理（`/config_management/system`）  
> 来源：平台功能模块知识库（本仓 `prj-docs`）

## 模块说明

组织机构、用户/分组、角色、场景(模块)、菜单、文件分类与角色授权等账号权限体系。

## 适用场景

账号权限、基础主数据、日志审计、门禁业务与信息发布等系统级管理场景。

## 功能页面

| 页面                 | 路径                | 路由                                          | 说明                                            |
| -------------------- | ------------------- | --------------------------------------------- | ----------------------------------------------- |
| 组织机构             | `organization`      | `/config_management/system/organization`      | 维护组织机构树。                                |
| 用户分组             | `user_group`        | `/config_management/system/user_group`        | 管理用户分组。                                  |
| 用户管理             | `user_manage`       | `/config_management/system/user_manage`       | 创建/编辑用户账号与归属。                       |
| 角色管理             | `role_manage`       | `/config_management/system/role_manage`       | 维护角色定义。                                  |
| 场景管理             | `module_manage`     | `/config_management/system/module_manage`     | 场景/模块管理，控制门户可见业务模块与设备范围。 |
| 模块诊断（菜单隐藏） | `module_diagnostic` | `/config_management/system/module_diagnostic` | 模块诊断（菜单默认隐藏）。                      |
| 菜单管理             | `menu_manage`       | `/config_management/system/menu_manage`       | 配置系统菜单树、图标与展示属性。                |
| 文件分类             | `file_category`     | `/config_management/system/file_category`     | 文件分类字典。                                  |
| 角色授权             | `role_auth`         | `/config_management/system/role_auth`         | 为角色授权菜单与功能权限。                      |

## 操作指引（通用）

1. 登录综合信息管理平台，从门户进入「配置管理平台」。
2. 打开左侧「系统管理」→「用户及参数管理」。
3. 在列表页按条件查询；通过新增/编辑/删除维护数据（具体按钮以页面为准）。
4. 若页面含树形筛选（区域/组织/类别），先选节点再操作右侧列表。
5. 无菜单权限时，请管理员在「角色授权 / 菜单管理」中分配。

## 关联依赖

门户菜单与模块可见性依赖场景管理与角色授权。

## 常见问题

- **看不到本模块菜单**：检查账号角色是否授权；超级管理员可在「菜单管理 / 角色授权 / 场景管理」配置。
- **列表无数据**：确认筛选条件、所属区域/组织节点，以及后端服务与数据权限范围。
- **无法保存**：检查必填项、字典引用是否存在，以及是否具备写权限。

## 代码定位

- 功能分组：`groupId: user`
- 对应平台配置管理功能页面
