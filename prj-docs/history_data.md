# 历史数据查询统计

> 英文名：History Data Query Statistics  
> 模块 ID：`history_data`  
> 所属业务域：配置管理（`/config_management/config`）  
> 来源：平台功能模块知识库（本仓 `prj-docs`）

## 模块说明

历史数据查询、曲线分析、导出模板、设备索引、导出任务与数据修复。

## 适用场景

设备接入、变量采集、事件联动、周界安防、报警与历史数据分析等配置与运维场景。

## 功能页面

| 页面                     | 路径                           | 路由                                                     | 说明                               |
| ------------------------ | ------------------------------ | -------------------------------------------------------- | ---------------------------------- |
| 历史数据查询             | `history_query`                | `/config_management/config/history_query`                | 按设备/变量/时间查询历史测点数据。 |
| 导出模板配置             | `query_template_configuration` | `/config_management/config/query_template_configuration` | 配置历史数据导出模板。             |
| 设备索引                 | `device_registry_index`        | `/config_management/config/device_registry_index`        | 维护历史库设备索引。               |
| 任务管理                 | `task_manage`                  | `/config_management/config/task_manage`                  | 管理历史数据导出/查询任务。        |
| 历史曲线查询             | `history_statistics`           | `/config_management/config/history_statistics`           | 历史曲线查询与对比。               |
| 历史数据修复（菜单隐藏） | `history_data_repair`          | `/config_management/config/history_data_repair`          | 修复异常历史数据（默认菜单隐藏）。 |

## 操作指引（通用）

1. 登录综合信息管理平台，从门户进入「配置管理平台」。
2. 打开左侧「配置管理」→「历史数据查询统计」。
3. 在列表页按条件查询；通过新增/编辑/删除维护数据（具体按钮以页面为准）。
4. 若页面含树形筛选（区域/组织/类别），先选节点再操作右侧列表。
5. 无菜单权限时，请管理员在「角色授权 / 菜单管理」中分配。

## 关联依赖

依赖设备变量入库与设备索引；导出任务依赖模板配置。

## 常见问题

- **看不到本模块菜单**：检查账号角色是否授权；超级管理员可在「菜单管理 / 角色授权 / 场景管理」配置。
- **列表无数据**：确认筛选条件、所属区域/组织节点，以及后端服务与数据权限范围。
- **无法保存**：检查必填项、字典引用是否存在，以及是否具备写权限。

## 代码定位

- 功能分组：`groupId: history_data`
- 对应平台配置管理功能页面
