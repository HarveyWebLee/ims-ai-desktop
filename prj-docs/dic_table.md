# 字典表

> 英文名：Dictionary Table  
> 模块 ID：`dic_table`  
> 所属业务域：系统管理（`/config_management/system`）  
> 来源：平台功能模块知识库（本仓 `prj-docs`）

## 模块说明

报警级别/类型/源、职务军衔、风向、国别技能专业等信息发布与业务字典维护。

## 适用场景

账号权限、基础主数据、日志审计、门禁业务与信息发布等系统级管理场景。

## 功能页面

| 页面         | 路径                 | 路由                                           | 说明                                           |
| ------------ | -------------------- | ---------------------------------------------- | ---------------------------------------------- |
| 报警级别     | `alarm_level`        | `/config_management/system/alarm_level`        | 维护对应业务字典项，供其它模块下拉与校验引用。 |
| 报警类型     | `alarm_category`     | `/config_management/system/alarm_category`     | 维护对应业务字典项，供其它模块下拉与校验引用。 |
| 报警源       | `alarm_source`       | `/config_management/system/alarm_source`       | 维护对应业务字典项，供其它模块下拉与校验引用。 |
| 职务         | `job`                | `/config_management/system/job`                | 维护对应业务字典项，供其它模块下拉与校验引用。 |
| 军衔         | `military_rank`      | `/config_management/system/military_rank`      | 维护对应业务字典项，供其它模块下拉与校验引用。 |
| 风向         | `wind_direction`     | `/config_management/system/wind_direction`     | 维护对应业务字典项，供其它模块下拉与校验引用。 |
| 信息发布状态 | `info_release_state` | `/config_management/system/info_release_state` | 维护对应业务字典项，供其它模块下拉与校验引用。 |
| 物体类别     | `object_class`       | `/config_management/system/object_class`       | 维护对应业务字典项，供其它模块下拉与校验引用。 |
| 国别         | `nationality`        | `/config_management/system/nationality`        | 维护对应业务字典项，供其它模块下拉与校验引用。 |
| 技能         | `skill`              | `/config_management/system/skill`              | 维护对应业务字典项，供其它模块下拉与校验引用。 |
| 专业         | `major`              | `/config_management/system/major`              | 维护对应业务字典项，供其它模块下拉与校验引用。 |

## 操作指引（通用）

1. 登录综合信息管理平台，从门户进入「配置管理平台」。
2. 打开左侧「系统管理」→「字典表」。
3. 在列表页按条件查询；通过新增/编辑/删除维护数据（具体按钮以页面为准）。
4. 若页面含树形筛选（区域/组织/类别），先选节点再操作右侧列表。
5. 无菜单权限时，请管理员在「角色授权 / 菜单管理」中分配。

## 关联依赖

字典项被报警、人员、信息发布等表单引用。

## 常见问题

- **看不到本模块菜单**：检查账号角色是否授权；超级管理员可在「菜单管理 / 角色授权 / 场景管理」配置。
- **列表无数据**：确认筛选条件、所属区域/组织节点，以及后端服务与数据权限范围。
- **无法保存**：检查必填项、字典引用是否存在，以及是否具备写权限。

## 代码定位

- 功能分组：`groupId: dic_table`
- 对应平台配置管理功能页面
