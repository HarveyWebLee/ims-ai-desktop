# 设备连接图（device_connection_diagram）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                                             |
| ------------------ | -------------------------------------------------------------------------------- |
| 模块名称（中文）   | 设备连接图                                                                       |
| 模块名称（英文）   | Device Connection Diagram                                                        |
| 所属 Group（中文） | 监控设备                                                                         |
| 所属 Group（英文） | Monitor Equipment                                                                |
| Group ID           | `monitor_equipment`                                                              |
| 菜单位置           | 配置管理平台 → 配置管理 → 监控设备 → 设备连接图                                  |
| 路由路径           | `/config_management/config/device_connection_diagram`                            |
| 页面目录           | `src/pages/config_management/config/monitor_equipment/device_connection_diagram` |

## 1. 模块定位与项目作用

设备连接拓扑图是综合信息平台中「监控设备」业务域下的功能模块，对应页面目录 `src/pages/config_management/config/monitor_equipment/device_connection_diagram`。

在项目中的主要作用：

- 作为「配置管理平台 → 配置管理 → 监控设备 → 设备连接拓扑图」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
- 通过本模块维护或消费的数据，可能被同业务域其他页面、报表、组态或流程能力引用。
- 具体能力以页面交互与接口清单为准；变更本模块配置/数据时，应评估对上下游模块的影响。

---

## 4. 与其他功能模块的关系

### 4.1 同目录兄弟模块

| 关联模块                                | 关系说明 |
| --------------------------------------- | -------- |
| 设备动态属性（device_dynamic_property） | 同组     |
| 设备迁移（device_migrate）              | 同组     |
| 设备管理（equipment_manage）            | 同组     |

### 4.2 上游依赖 / 下游消费

- **上游**：用户及参数管理（`user`）、基础数据（`basedata`）。

---
