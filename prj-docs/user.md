# 用户及参数管理

> 英文名：User and Parameter Management  
> 模块 ID：`user`  
> 所属业务域：系统管理（`/config_management/system`）  
> 页面数：8  
> 上级索引：[README.md](./README.md) · 页面总表：[TOTAL-MODULE.md](./TOTAL-MODULE.md)  
> 来源：前端 routes 权威菜单

## 模块说明

用户及参数管理（`user`）。真实路由为 `parent/path`，**不含 groupId**；源码目录见详档「页面目录」。

## 功能页面

| 页面     | 路径            | 路由                                      | 详细文档                                                                                           |
| -------- | --------------- | ----------------------------------------- | -------------------------------------------------------------------------------------------------- |
| 文件分类 | `file_category` | `/config_management/system/file_category` | [config_management-system-user-file_category.md](./config_management-system-user-file_category.md) |
| 菜单管理 | `menu_manage`   | `/config_management/system/menu_manage`   | [config_management-system-user-menu_manage.md](./config_management-system-user-menu_manage.md)     |
| 场景管理 | `module_manage` | `/config_management/system/module_manage` | [config_management-system-user-module_manage.md](./config_management-system-user-module_manage.md) |
| 组织机构 | `organization`  | `/config_management/system/organization`  | [config_management-system-user-organization.md](./config_management-system-user-organization.md)   |
| 角色授权 | `role_auth`     | `/config_management/system/role_auth`     | [config_management-system-user-role_auth.md](./config_management-system-user-role_auth.md)         |
| 角色管理 | `role_manage`   | `/config_management/system/role_manage`   | [config_management-system-user-role_manage.md](./config_management-system-user-role_manage.md)     |
| 用户分组 | `user_group`    | `/config_management/system/user_group`    | [config_management-system-user-user_group.md](./config_management-system-user-user_group.md)       |
| 用户管理 | `user_manage`   | `/config_management/system/user_manage`   | [config_management-system-user-user_manage.md](./config_management-system-user-user_manage.md)     |

## 操作指引（通用）

1. 登录后进入「配置管理平台」。
2. 打开「系统管理」→「用户及参数管理」。
3. 按页面按钮维护数据；无权限时在「角色授权 / 菜单管理」分配。

## 代码定位

- `groupId: user`
