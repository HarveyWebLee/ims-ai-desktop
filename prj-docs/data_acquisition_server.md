# 数采服务器

> 英文名：Data Acquisition Server  
> 模块 ID：`data_acquisition_server`  
> 所属业务域：配置管理（`/config_management/config`）  
> 页面数：3  
> 上级索引：[README.md](./README.md) · 页面总表：[TOTAL-MODULE.md](./TOTAL-MODULE.md)  
> 来源：前端 routes 权威菜单

## 模块说明

数采服务器（`data_acquisition_server`）。真实路由为 `parent/path`，**不含 groupId**；源码目录见详档「页面目录」。

## 功能页面

| 页面       | 路径                   | 路由                                             | 详细文档                                                                                                                                               |
| ---------- | ---------------------- | ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 通信网关   | `communication_config` | `/config_management/config/communication_config` | [config_management-config-data_acquisition_server-communication_config.md](./config_management-config-data_acquisition_server-communication_config.md) |
| 数采服务器 | `das`                  | `/config_management/config/das`                  | [config_management-config-data_acquisition_server-das.md](./config_management-config-data_acquisition_server-das.md)                                   |
| 服务组件   | `service_component`    | `/config_management/config/service_component`    | [config_management-config-data_acquisition_server-service_component.md](./config_management-config-data_acquisition_server-service_component.md)       |

## 操作指引（通用）

1. 登录后进入「配置管理平台」。
2. 打开「配置管理」→「数采服务器」。
3. 按页面按钮维护数据；无权限时在「角色授权 / 菜单管理」分配。

## 代码定位

- `groupId: data_acquisition_server`
