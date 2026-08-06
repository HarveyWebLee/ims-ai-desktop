# 门禁系统

> 英文名：Door Access System  
> 模块 ID：`door_access_system`  
> 所属业务域：系统管理（`/config_management/system`）  
> 页面数：8  
> 上级索引：[README.md](./README.md) · 页面总表：[TOTAL-MODULE.md](./TOTAL-MODULE.md)  
> 来源：前端 routes 权威菜单

## 模块说明

门禁系统（`door_access_system`）。真实路由为 `parent/path`，**不含 groupId**；源码目录见详档「页面目录」。

## 功能页面

| 页面         | 路径                             | 路由                                                       | 详细文档                                                                                                                                                         |
| ------------ | -------------------------------- | ---------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 出入信息维护 | `access_information_maintenance` | `/config_management/system/access_information_maintenance` | [config_management-system-door_access_system-access_information_maintenance.md](./config_management-system-door_access_system-access_information_maintenance.md) |
| 出入信息统计 | `access_statistics`              | `/config_management/system/access_statistics`              | [config_management-system-door_access_system-access_statistics.md](./config_management-system-door_access_system-access_statistics.md)                           |
| 门禁信息同步 | `door_access_sync`               | `/config_management/system/door_access_sync`               | [config_management-system-door_access_system-door_access_sync.md](./config_management-system-door_access_system-door_access_sync.md)                             |
| 值班信息     | `duty_info`                      | `/config_management/system/duty_info`                      | [config_management-system-door_access_system-duty_info.md](./config_management-system-door_access_system-duty_info.md)                                           |
| 岗哨交接     | `guard_post_handover`            | `/config_management/system/guard_post_handover`            | [config_management-system-door_access_system-guard_post_handover.md](./config_management-system-door_access_system-guard_post_handover.md)                       |
| 出入信息管理 | `in_out_storage`                 | `/config_management/system/in_out_storage`                 | [config_management-system-door_access_system-in_out_storage.md](./config_management-system-door_access_system-in_out_storage.md)                                 |
| 出入库管理   | `inner_storage`                  | `/config_management/system/inner_storage`                  | [config_management-system-door_access_system-inner_storage.md](./config_management-system-door_access_system-inner_storage.md)                                   |
| 安全检查     | `safety_check`                   | `/config_management/system/safety_check`                   | [config_management-system-door_access_system-safety_check.md](./config_management-system-door_access_system-safety_check.md)                                     |

## 操作指引（通用）

1. 登录后进入「配置管理平台」。
2. 打开「系统管理」→「门禁系统」。
3. 按页面按钮维护数据；无权限时在「角色授权 / 菜单管理」分配。

## 代码定位

- `groupId: door_access_system`
