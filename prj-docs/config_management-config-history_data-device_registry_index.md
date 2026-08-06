# 设备索引（device_registry_index）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                                    |
| ------------------ | ----------------------------------------------------------------------- |
| 模块名称（中文）   | 设备索引                                                                |
| 模块名称（英文）   | Device Registry Index                                                   |
| 所属 Group（中文） | 历史数据查询统计                                                        |
| 所属 Group（英文） | History Data Query Statistics                                           |
| Group ID           | `history_data`                                                          |
| 菜单位置           | 配置管理平台 → 配置管理 → 历史数据查询统计 → 设备索引                   |
| 路由路径           | `/config_management/config/device_registry_index`                       |
| 页面目录           | `src/pages/config_management/config/history_data/device_registry_index` |

## 1. 模块定位与项目作用

设备注册索引是综合信息平台中「历史数据查询统计」业务域下的功能模块，对应页面目录 `src/pages/config_management/config/history_data/device_registry_index`。

在项目中的主要作用：

- 作为「配置管理平台 → 配置管理 → 历史数据 → 设备注册索引」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
- 通过本模块维护或消费的数据，可能被同业务域其他页面、报表、组态或流程能力引用。
- 具体能力以页面交互与接口清单为准；变更本模块配置/数据时，应评估对上下游模块的影响。

---

## 3. 属性字段说明

以下字段由页面代码启发式提取，用于快速了解主数据形态；若与线上表单不一致，以实际页面与接口契约为准。

| 字段名 | 中文含义 | 作用说明                        |
| ------ | -------- | ------------------------------- |
| isDel  | 索引状态 | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

---

- 复制

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                                     | 关系说明 |
| -------------------------------------------- | -------- |
| 历史数据修复（history_data_repair）          | 同组     |
| 历史数据查询（history_query）                | 同组     |
| 历史数据统计（history_statistics）           | 同组     |
| 查询模板配置（query_template_configuration） | 同组     |
| 任务管理（task_manage）                      | 同组     |

### 5.2 上游依赖 / 下游消费

- **上游**：监控设备（`monitor_equipment`）、用户及参数管理（`user`）、基础数据（`basedata`）。

---
