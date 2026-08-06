# 质量统计（quality_statistics）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                                                         |
| ------------------ | -------------------------------------------------------------------------------------------- |
| 模块名称（中文）   | 质量统计                                                                                     |
| 模块名称（英文）   | Quality Statistics                                                                           |
| 所属 Group（中文） | 设施设备管理                                                                                 |
| 所属 Group（英文） | Facilities and Equipment Management                                                          |
| Group ID           | `facilities_management`                                                                      |
| 菜单位置           | 配置管理平台 → 阵地维护管理 → 设施设备管理 → 质量统计                                        |
| 路由路径           | `/config_management/positional_management/quality_statistics`                                |
| 页面目录           | `src/pages/config_management/positional_management/facilities_management/quality_statistics` |

## 1. 模块定位与项目作用

质量统计是综合信息平台中「设施设备管理」业务域下的功能模块，对应页面目录 `src/pages/config_management/positional_management/facilities_management/quality_statistics`。

在项目中的主要作用：

- 作为「配置管理平台 → 阵地维护管理 → 设施设备管理 → 质量统计」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
- 通过本模块维护或消费的数据，可能被同业务域其他页面、报表、组态或流程能力引用。
- 具体能力以页面交互与接口清单为准；变更本模块配置/数据时，应评估对上下游模块的影响。

---

## 4. 与其他功能模块的关系

### 4.1 同目录兄弟模块

| 关联模块                                    | 关系说明 |
| ------------------------------------------- | -------- |
| 属性字典（attribute_dictionary）            | 同组     |
| 分类管理（category_management）             | 同组     |
| 设施管理（facility_management）             | 同组     |
| 交接管理（handover_management）             | 同组     |
| 安装位置管理（install_position_management） | 同组     |
| 使用（usage）                               | 同组     |

### 4.2 上游依赖 / 下游消费

- **上游**：用户及参数管理（`user`）、基础数据（`basedata`）。

---
