# 基础数据

> 英文名：Basic Data  
> 模块 ID：`basedata`  
> 所属业务域：系统管理（`/config_management/system`）  
> 来源：平台功能模块知识库（本仓 `prj-docs`）

## 模块说明

区域、设备类型/分组、人员统计、访问组、岗哨、区间、监控任务等基础主数据。

## 适用场景

账号权限、基础主数据、日志审计、门禁业务与信息发布等系统级管理场景。

## 功能页面

| 页面     | 路径                   | 路由                                             | 说明                      |
| -------- | ---------------------- | ------------------------------------------------ | ------------------------- |
| 区域管理 | `region_tree`          | `/config_management/system/region_tree`          | 维护区域树（场所/分区）。 |
| 设备类型 | `device_type`          | `/config_management/system/device_type`          | 设备类型字典。            |
| 设备分组 | `device_group`         | `/config_management/system/device_group`         | 设备分组。                |
| 人员统计 | `personnel_statistics` | `/config_management/system/personnel_statistics` | 人员相关统计。            |
| 访问组   | `access_group`         | `/config_management/system/access_group`         | 访问组（门禁/权限范围）。 |
| 岗哨信息 | `guard_post_info`      | `/config_management/system/guard_post_info`      | 岗哨基础信息。            |
| 区间设置 | `interval_setting`     | `/config_management/system/interval_setting`     | 区间参数设置。            |
| 监控任务 | `monitoring_task`      | `/config_management/system/monitoring_task`      | 监控任务配置。            |

## 操作指引（通用）

1. 登录综合信息管理平台，从门户进入「配置管理平台」。
2. 打开左侧「系统管理」→「基础数据」。
3. 在列表页按条件查询；通过新增/编辑/删除维护数据（具体按钮以页面为准）。
4. 若页面含树形筛选（区域/组织/类别），先选节点再操作右侧列表。
5. 无菜单权限时，请管理员在「角色授权 / 菜单管理」中分配。

## 关联依赖

区域、设备类型等被配置管理与门禁等模块广泛引用。

## 常见问题

- **看不到本模块菜单**：检查账号角色是否授权；超级管理员可在「菜单管理 / 角色授权 / 场景管理」配置。
- **列表无数据**：确认筛选条件、所属区域/组织节点，以及后端服务与数据权限范围。
- **无法保存**：检查必填项、字典引用是否存在，以及是否具备写权限。

## 代码定位

- 功能分组：`groupId: basedata`
- 对应平台配置管理功能页面
