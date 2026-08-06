# 周界防区设定

> 英文名：Perimeter Zone Setting  
> 模块 ID：`perimeter_setting`  
> 所属业务域：配置管理（`/config_management/config`）  
> 页面数：4  
> 上级索引：[README.md](./README.md) · 页面总表：[TOTAL-MODULE.md](./TOTAL-MODULE.md)  
> 来源：前端 routes 权威菜单

## 模块说明

周界防区设定（`perimeter_setting`）。真实路由为 `parent/path`，**不含 groupId**；源码目录见详档「页面目录」。

## 功能页面

| 页面       | 路径                  | 路由                                            | 详细文档                                                                                                                                 |
| ---------- | --------------------- | ----------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| 撤布防记录 | `evacuation_record`   | `/config_management/config/evacuation_record`   | [config_management-config-perimeter_setting-evacuation_record.md](./config_management-config-perimeter_setting-evacuation_record.md)     |
| 防区列表   | `group`               | `/config_management/config/group`               | [config_management-config-perimeter_setting-group.md](./config_management-config-perimeter_setting-group.md)                             |
| 防区维护   | `maintenance`         | `/config_management/config/maintenance`         | [config_management-config-perimeter_setting-maintenance.md](./config_management-config-perimeter_setting-maintenance.md)                 |
| 手动撤布防 | `manual_cycle_disarm` | `/config_management/config/manual_cycle_disarm` | [config_management-config-perimeter_setting-manual_cycle_disarm.md](./config_management-config-perimeter_setting-manual_cycle_disarm.md) |

## 操作指引（通用）

1. 登录后进入「配置管理平台」。
2. 打开「配置管理」→「周界防区设定」。
3. 按页面按钮维护数据；无权限时在「角色授权 / 菜单管理」分配。

## 代码定位

- `groupId: perimeter_setting`
