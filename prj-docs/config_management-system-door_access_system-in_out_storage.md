# 出入信息管理（in_out_storage）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                                   |
| ------------------ | ---------------------------------------------------------------------- |
| 模块名称（中文）   | 出入信息管理                                                           |
| 模块名称（英文）   | In Out Storage                                                         |
| 所属 Group（中文） | 门禁系统                                                               |
| 所属 Group（英文） | Door Access System                                                     |
| Group ID           | `door_access_system`                                                   |
| 菜单位置           | 配置管理平台 → 系统管理 → 门禁系统 → 出入信息管理                      |
| 路由路径           | `/config_management/system/in_out_storage`                             |
| 页面目录           | `src/pages/config_management/system/door_access_system/in_out_storage` |

## 1. 模块定位与项目作用

入出仓储是综合信息平台中「门禁系统」业务域下的功能模块，对应页面目录 `src/pages/config_management/system/door_access_system/in_out_storage`。

在项目中的主要作用：

- 作为「配置管理平台 → 系统管理 → 门禁系统 → 入出仓储」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
- 通过本模块维护或消费的数据，可能被同业务域其他页面、报表、组态或流程能力引用。
- 具体能力以页面交互与接口清单为准；变更本模块配置/数据时，应评估对上下游模块的影响。

---

## 3. 属性字段说明

以下字段由页面代码启发式提取，用于快速了解主数据形态；若与线上表单不一致，以实际页面与接口契约为准。

| 字段名          | 中文含义         | 作用说明                        |
| --------------- | ---------------- | ------------------------------- |
| deviceGroupName | 所属子系统       | 模块表单/列表字段，详见页面配置 |
| subSystemName   | 所属区域         | 模块表单/列表字段，详见页面配置 |
| regionName      | 设备名称         | 模块表单/列表字段，详见页面配置 |
| deviceCode      | 门名称           | 模块表单/列表字段，详见页面配置 |
| deviceName      | 申请单位         | 模块表单/列表字段，详见页面配置 |
| teamLeaderId    | 带队人           | 模块表单/列表字段，详见页面配置 |
| teamLeaderName  | 职务             | 模块表单/列表字段，详见页面配置 |
| position        | 活动区域         | 模块表单/列表字段，详见页面配置 |
| outTime         | 入库人数         | 模块表单/列表字段，详见页面配置 |
| deviceStatus    | 设备启用状态     | 模块表单/列表字段，详见页面配置 |
| applyUnit       | 申请单位         | 模块表单/列表字段，详见页面配置 |
| activeArea      | 活动区域         | 模块表单/列表字段，详见页面配置 |
| inTime          | 入库时间         | 模块表单/列表字段，详见页面配置 |
| inCount         | 入库人数         | 模块表单/列表字段，详见页面配置 |
| inReason        | 入库事由         | 模块表单/列表字段，详见页面配置 |
| allPersonInfo   | 随行入库人员信息 | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

---

- 复制

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                                                         | 关系说明 |
| ---------------------------------------------------------------- | -------- |
| Access Information Maintenance（access_information_maintenance） | 同组     |
| 门禁统计（access_statistics）                                    | 同组     |
| door门禁同步（door_access_sync）                                 | 同组     |
| 执勤信息（duty_info）                                            | 同组     |
| 哨位岗位交接（guard_post_handover）                              | 同组     |
| 内部仓储（inner_storage）                                        | 同组     |
| 安全检查（safety_check）                                         | 同组     |

### 5.2 上游依赖 / 下游消费

- **上游**：用户及参数管理（`user`）、监控设备（`monitor_equipment`）、基础数据（`basedata`）。

---
