# 采集器（harvester）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                          |
| ------------------ | ------------------------------------------------------------- |
| 模块名称（中文）   | 采集器                                                        |
| 模块名称（英文）   | Harvester Monitor                                             |
| 所属 Group（中文） | 系统监控                                                      |
| 所属 Group（英文） | System Monitor                                                |
| Group ID           | `system_monitor`                                              |
| 菜单位置           | 配置管理平台 → 配置管理 → 系统监控 → 采集器                   |
| 路由路径           | `/config_management/config/harvester`                         |
| 页面目录           | `src/pages/config_management/config/system_monitor/harvester` |

## 1. 模块定位与项目作用

采集器监控是综合信息平台中「系统监控」业务域下的功能模块，对应页面目录 `src/pages/config_management/config/system_monitor/harvester`。

在项目中的主要作用：

- 作为「配置管理平台 → 配置管理 → 系统监控 → 采集器监控」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
- 通过本模块维护或消费的数据，可能被同业务域其他页面、报表、组态或流程能力引用。
- 具体能力以页面交互与接口清单为准；变更本模块配置/数据时，应评估对上下游模块的影响。

---

## 3. 属性字段说明

以下字段由页面代码启发式提取，用于快速了解主数据形态；若与线上表单不一致，以实际页面与接口契约为准。

| 字段名          | 中文含义                 | 作用说明                        |
| --------------- | ------------------------ | ------------------------------- |
| Type            | harvester.totalMemoryMB  | 模块表单/列表字段，详见页面配置 |
| Total           | harvester.freeMemoryMB   | 模块表单/列表字段，详见页面配置 |
| Free            | harvester.usedMemoryMB   | 模块表单/列表字段，详见页面配置 |
| Used            | harvester.sharedMemoryMB | 模块表单/列表字段，详见页面配置 |
| Shared          | harvester.bufferCacheMB  | 模块表单/列表字段，详见页面配置 |
| deviceCode      | harvester.taskStatus     | 模块表单/列表字段，详见页面配置 |
| Filesystem      | harvester.totalSize      | 模块表单/列表字段，详见页面配置 |
| Size            | harvester.available      | 模块表单/列表字段，详见页面配置 |
| Available       | harvester.used           | 模块表单/列表字段，详见页面配置 |
| UsagePercentage | harvester.mountPoint     | 模块表单/列表字段，详见页面配置 |
| status          | harvester.taskStatus     | 模块表单/列表字段，详见页面配置 |
| mountPoint      | harvester.mountPoint     | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

---

- 分页查询

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                     | 关系说明 |
| ---------------------------- | -------- |
| 历史数据监控（history_data） | 同组     |

### 5.2 上游依赖 / 下游消费

- **上游**：用户及参数管理（`user`）。

---
