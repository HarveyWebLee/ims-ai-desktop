# 统计（statistics）知识库

## 0. 路由与归属信息

| 项                 | 内容                   |
| ------------------ | ---------------------- |
| 模块名称（中文）   | 统计                   |
| 模块名称（英文）   | Statistics             |
| 所属 Group（中文） | 统计                   |
| 所属 Group（英文） | Statistics             |
| Group ID           | `statistics`           |
| 菜单位置           | 统计                   |
| 路由路径           | `/statistics`          |
| 页面目录           | `src/pages/statistics` |

## 1. 模块定位与项目作用

统计是综合信息平台中「统计」业务域下的功能模块，对应页面目录 `src/pages/statistics`。

在项目中的主要作用：

- 作为「统计」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
- 通过本模块维护或消费的数据，可能被同业务域其他页面、报表、组态或流程能力引用。
- 具体能力以页面交互与接口清单为准；变更本模块配置/数据时，应评估对上下游模块的影响。

---

## 4. 与其他功能模块的关系

### 4.1 相关统计与数据源

| 关联模块         | 文档                                                     | 关系说明               |
| ---------------- | -------------------------------------------------------- | ---------------------- |
| 门禁统计         | [door_statistics.md](./door_statistics.md)               | 门禁维度统计展示       |
| 库房统计         | [storage_statistics.md](./storage_statistics.md)         | 库房维度统计展示       |
| 报警查询统计     | [alarm_query_statistics.md](./alarm_query_statistics.md) | 配置侧报警统计能力     |
| 历史数据查询统计 | [history_data.md](./history_data.md)                     | 历史趋势与统计         |
| 总览             | [overview.md](./overview.md)                             | 门户入口，可导航至统计 |

### 4.2 上游依赖 / 下游消费

- **上游**：用户及参数管理（`user`）、监控设备（`monitor_equipment`）、设备变量（`device_variable`）。
- **下游**：供值班指挥与运维决策查看，一般不回写业务主数据。
