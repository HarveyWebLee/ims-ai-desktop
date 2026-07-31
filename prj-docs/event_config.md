# 事件配置

> 英文名：Event Config  
> 模块 ID：`event_config`  
> 所属业务域：配置管理（`/config_management/config`）  
> 来源：平台功能模块知识库（本仓 `prj-docs`）

## 模块说明

配置事件流、事件联动规则、周期事件，并查询事件执行与联动记录。

## 适用场景

设备接入、变量采集、事件联动、周界安防、报警与历史数据分析等配置与运维场景。

## 功能页面

| 页面                     | 路径                       | 路由                                                 | 说明                               |
| ------------------------ | -------------------------- | ---------------------------------------------------- | ---------------------------------- |
| 事件流配置（菜单隐藏）   | `event_flow_config`        | `/config_management/config/event_flow_config`        | 配置事件流（菜单默认隐藏）。       |
| 事件执行记录（菜单隐藏） | `event_execution_record`   | `/config_management/config/event_execution_record`   | 查看事件执行历史（菜单默认隐藏）。 |
| 事件联动规则             | `event_link_rule`          | `/config_management/config/event_link_rule`          | 配置条件触发的事件联动动作。       |
| 高级事件联动（菜单隐藏） | `event_link_rule_advanced` | `/config_management/config/event_link_rule_advanced` | 高级事件联动配置（菜单默认隐藏）。 |
| 事件联动记录表           | `event_rule_record`        | `/config_management/config/event_rule_record`        | 查看事件联动历史记录。             |
| 周期事件配置             | `cycle_event_config`       | `/config_management/config/cycle_event_config`       | 配置按周期触发的事件。             |

## 操作指引（通用）

1. 登录综合信息管理平台，从门户进入「配置管理平台」。
2. 打开左侧「配置管理」→「事件配置」。
3. 在列表页按条件查询；通过新增/编辑/删除维护数据（具体按钮以页面为准）。
4. 若页面含树形筛选（区域/组织/类别），先选节点再操作右侧列表。
5. 无菜单权限时，请管理员在「角色授权 / 菜单管理」中分配。

## 关联依赖

依赖设备变量与报警配置；执行结果可在联动记录中追溯。

## 常见问题

- **看不到本模块菜单**：检查账号角色是否授权；超级管理员可在「菜单管理 / 角色授权 / 场景管理」配置。
- **列表无数据**：确认筛选条件、所属区域/组织节点，以及后端服务与数据权限范围。
- **无法保存**：检查必填项、字典引用是否存在，以及是否具备写权限。

## 代码定位

- 功能分组：`groupId: event_config`
- 对应平台配置管理功能页面
