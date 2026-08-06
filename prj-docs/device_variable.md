# 设备变量

> 英文名：Device Variable  
> 模块 ID：`device_variable`  
> 所属业务域：配置管理（`/config_management/config`）  
> 页面数：4  
> 上级索引：[README.md](./README.md) · 页面总表：[TOTAL-MODULE.md](./TOTAL-MODULE.md)  
> 来源：前端 routes 权威菜单

## 模块说明

设备变量（`device_variable`）。真实路由为 `parent/path`，**不含 groupId**；源码目录见详档「页面目录」。

## 功能页面

| 页面         | 路径                 | 路由                                           | 详细文档                                                                                                                           |
| ------------ | -------------------- | ---------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| 实时数据     | `real_time_var_data` | `/config_management/config/real_time_var_data` | [config_management-config-device_variable-real_time_var_data.md](./config_management-config-device_variable-real_time_var_data.md) |
| 二次变量     | `second_var`         | `/config_management/config/second_var`         | [config_management-config-device_variable-second_var.md](./config_management-config-device_variable-second_var.md)                 |
| 设备变量     | `var`                | `/config_management/config/var`                | [config_management-config-device_variable-var.md](./config_management-config-device_variable-var.md)                               |
| 变量报警配置 | `var_alarm_config`   | `/config_management/config/var_alarm_config`   | [config_management-config-device_variable-var_alarm_config.md](./config_management-config-device_variable-var_alarm_config.md)     |

## 操作指引（通用）

1. 登录后进入「配置管理平台」。
2. 打开「配置管理」→「设备变量」。
3. 按页面按钮维护数据；无权限时在「角色授权 / 菜单管理」分配。

## 代码定位

- `groupId: device_variable`
