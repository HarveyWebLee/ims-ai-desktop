# 值班信息（duty_info）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                              |
| ------------------ | ----------------------------------------------------------------- |
| 模块名称（中文）   | 值班信息                                                          |
| 模块名称（英文）   | Duty Info                                                         |
| 所属 Group（中文） | 门禁系统                                                          |
| 所属 Group（英文） | Door Access System                                                |
| Group ID           | `door_access_system`                                              |
| 菜单位置           | 配置管理平台 → 系统管理 → 门禁系统 → 值班信息                     |
| 路由路径           | `/config_management/system/duty_info`                             |
| 页面目录           | `src/pages/config_management/system/door_access_system/duty_info` |

## 1. 模块定位与项目作用

执勤信息是综合信息平台中「门禁系统」业务域下的功能模块，对应页面目录 `src/pages/config_management/system/door_access_system/duty_info`。

在项目中的主要作用：

- 作为「配置管理平台 → 系统管理 → 门禁系统 → 执勤信息」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
- 通过本模块维护或消费的数据，可能被同业务域其他页面、报表、组态或流程能力引用。
- 具体能力以页面交互与接口清单为准；变更本模块配置/数据时，应评估对上下游模块的影响。

---

## 3. 属性字段说明

以下字段由页面代码启发式提取，用于快速了解主数据形态；若与线上表单不一致，以实际页面与接口契约为准。

| 字段名             | 中文含义    | 作用说明                        |
| ------------------ | ----------- | ------------------------------- |
| handoverSupervisor | 交班值班员1 | 模块表单/列表字段，详见页面配置 |
| handDutyPerson1    | 交班值班员2 | 模块表单/列表字段，详见页面配置 |
| handDutyPerson2    | 交班值班员3 | 模块表单/列表字段，详见页面配置 |
| handDutyPerson3    | 交班值班员4 | 模块表单/列表字段，详见页面配置 |
| takeoverSupervisor | 接班值班员1 | 模块表单/列表字段，详见页面配置 |
| takeDutyPerson1    | 接班值班员2 | 模块表单/列表字段，详见页面配置 |
| takeDutyPerson2    | 接班值班员3 | 模块表单/列表字段，详见页面配置 |
| takeDutyPerson3    | 接班值班员4 | 模块表单/列表字段，详见页面配置 |
| handDutyPerson4    | 交班值班员4 | 模块表单/列表字段，详见页面配置 |
| takeDutyPerson4    | 接班值班员4 | 模块表单/列表字段，详见页面配置 |
| handoverTime       | 交接班时间  | 模块表单/列表字段，详见页面配置 |
| handoverSituation  | 交接班情况  | 模块表单/列表字段，详见页面配置 |
| remark             | 备注        | 模块表单/列表字段，详见页面配置 |

---

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                                                         | 关系说明 |
| ---------------------------------------------------------------- | -------- |
| Access Information Maintenance（access_information_maintenance） | 同组     |
| 门禁统计（access_statistics）                                    | 同组     |
| door门禁同步（door_access_sync）                                 | 同组     |
| 哨位岗位交接（guard_post_handover）                              | 同组     |
| 入出仓储（in_out_storage）                                       | 同组     |
| 内部仓储（inner_storage）                                        | 同组     |
| 安全检查（safety_check）                                         | 同组     |

### 5.2 上游依赖 / 下游消费

- **上游**：日常值班（`daily_duty`）、用户及参数管理（`user`）、基础数据（`basedata`）。

---
