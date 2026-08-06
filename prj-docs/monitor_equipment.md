# 监控设备

> 英文名：Monitor Equipment  
> 模块 ID：`monitor_equipment`  
> 所属业务域：配置管理（`/config_management/config`）  
> 页面数：4  
> 上级索引：[README.md](./README.md) · 页面总表：[TOTAL-MODULE.md](./TOTAL-MODULE.md)  
> 来源：前端 routes 权威菜单

## 模块说明

监控设备（`monitor_equipment`）。真实路由为 `parent/path`，**不含 groupId**；源码目录见详档「页面目录」。

## 功能页面

| 页面         | 路径                        | 路由                                                  | 详细文档                                                                                                                                             |
| ------------ | --------------------------- | ----------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| 设备连接图   | `device_connection_diagram` | `/config_management/config/device_connection_diagram` | [config_management-config-monitor_equipment-device_connection_diagram.md](./config_management-config-monitor_equipment-device_connection_diagram.md) |
| 设备动态属性 | `device_dynamic_property`   | `/config_management/config/device_dynamic_property`   | [config_management-config-monitor_equipment-device_dynamic_property.md](./config_management-config-monitor_equipment-device_dynamic_property.md)     |
| 设备迁移     | `device_migrate`            | `/config_management/config/device_migrate`            | [config_management-config-monitor_equipment-device_migrate.md](./config_management-config-monitor_equipment-device_migrate.md)                       |
| 设备管理     | `equipment_manage`          | `/config_management/config/equipment_manage`          | [config_management-config-monitor_equipment-equipment_manage.md](./config_management-config-monitor_equipment-equipment_manage.md)                   |

## 操作指引（通用）

1. 登录后进入「配置管理平台」。
2. 打开「配置管理」→「监控设备」。
3. 按页面按钮维护数据；无权限时在「角色授权 / 菜单管理」分配。

## 代码定位

- `groupId: monitor_equipment`
