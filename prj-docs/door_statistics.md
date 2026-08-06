# 门禁统计（door_statistics）知识库

## 0. 路由与归属信息

| 项                 | 内容                        |
| ------------------ | --------------------------- |
| 模块名称（中文）   | 门禁统计                    |
| 模块名称（英文）   | Door Statistics             |
| 所属 Group（中文） | 门禁统计                    |
| 所属 Group（英文） | Door Statistics             |
| Group ID           | `door_statistics`           |
| 菜单位置           | 门禁统计                    |
| 路由路径           | `/door_statistics`          |
| 页面目录           | `src/pages/door_statistics` |

## 1. 模块定位与项目作用

门禁统计是综合信息平台中「门禁统计」业务域下的功能模块，对应页面目录 `src/pages/door_statistics`。

在项目中的主要作用：

- 作为「门禁统计」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
- 通过本模块维护或消费的数据，可能被同业务域其他页面、报表、组态或流程能力引用。
- 具体能力以页面交互与接口清单为准；变更本模块配置/数据时，应评估对上下游模块的影响。

---

## 3. 属性字段说明

以下字段由页面代码启发式提取，用于快速了解主数据形态；若与线上表单不一致，以实际页面与接口契约为准。

| 字段名           | 中文含义                          | 作用说明                        |
| ---------------- | --------------------------------- | ------------------------------- |
| enterCount       | storageStatisticsOut              | 模块表单/列表字段，详见页面配置 |
| outCount         | storageStatisticsInStock          | 模块表单/列表字段，详见页面配置 |
| applyUnit        | doorStatisticsTeamLeader          | 模块表单/列表字段，详见页面配置 |
| teamLeaderName   | storageStatisticsMilitaryPosition | 模块表单/列表字段，详见页面配置 |
| position         | doorStatisticsActiveArea          | 模块表单/列表字段，详见页面配置 |
| activeArea       | doorStatisticsInTime              | 模块表单/列表字段，详见页面配置 |
| inTime           | doorStatisticsInCount             | 模块表单/列表字段，详见页面配置 |
| inCount          | doorStatisticsInReason            | 模块表单/列表字段，详见页面配置 |
| inReason         | doorStatisticsOutTime             | 模块表单/列表字段，详见页面配置 |
| outTime          | order                             | 模块表单/列表字段，详见页面配置 |
| name             | operation                         | 模块表单/列表字段，详见页面配置 |
| personName       | storageStatisticsCardNo           | 模块表单/列表字段，详见页面配置 |
| cardNo           | unit                              | 模块表单/列表字段，详见页面配置 |
| unitName         | storageStatisticsMilitaryPosition | 模块表单/列表字段，详见页面配置 |
| militaryPosition | storageStatisticsTime             | 模块表单/列表字段，详见页面配置 |
| time             | storageStatisticsTime             | 模块表单/列表字段，详见页面配置 |

---

## 5. 与其他功能模块的关系

### 5.1 相关模块

| 关联模块 | 文档                                             | 关系说明                      |
| -------- | ------------------------------------------------ | ----------------------------- |
| 门禁系统 | [door_access_system.md](./door_access_system.md) | 统计数据主要来自门禁业务      |
| 统计     | [statistics.md](./statistics.md)                 | 同属门户统计展示能力          |
| 基础数据 | [basedata.md](./basedata.md)                     | 岗哨、访问组、人员/卡等主数据 |

### 5.2 上游依赖 / 下游消费

- **上游**：用户及参数管理（`user`）、监控设备（`monitor_equipment`）、基础数据（`basedata`）。
- **下游**：门户展示与决策查看。
