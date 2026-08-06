# 工具管理（tool_management）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                                                 |
| ------------------ | ------------------------------------------------------------------------------------ |
| 模块名称（中文）   | 工具管理                                                                             |
| 模块名称（英文）   | Tool Management                                                                      |
| 所属 Group（中文） | 工具资料                                                                             |
| 所属 Group（英文） | Tools and Materials                                                                  |
| Group ID           | `tool_information`                                                                   |
| 菜单位置           | 配置管理平台 → 阵地维护管理 → 工具资料 → 工具管理                                    |
| 路由路径           | `/config_management/positional_management/tool_management`                           |
| 页面目录           | `src/pages/config_management/positional_management/tool_information/tool_management` |

## 1. 模块定位与项目作用

工具管理是综合信息平台中「工具资料」业务域下的功能模块，对应页面目录 `src/pages/config_management/positional_management/tool_information/tool_management`。

在项目中的主要作用：

- 作为「配置管理平台 → 阵地维护管理 → 工具资料 → 工具管理」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
- 通过本模块维护或消费的数据，可能被同业务域其他页面、报表、组态或流程能力引用。
- 具体能力以页面交互与接口清单为准；变更本模块配置/数据时，应评估对上下游模块的影响。

---

## 3. 属性字段说明

以下字段由页面代码启发式提取，用于快速了解主数据形态；若与线上表单不一致，以实际页面与接口契约为准。

| 字段名            | 中文含义 | 作用说明                        |
| ----------------- | -------- | ------------------------------- |
| toolTypeId        | 工具类型 | 模块表单/列表字段，详见页面配置 |
| toolName          | 名称     | 模块表单/列表字段，详见页面配置 |
| toolModel         | 工具型号 | 模块表单/列表字段，详见页面配置 |
| toolCode          | 工具编号 | 模块表单/列表字段，详见页面配置 |
| matchingTime      | 配套时间 | 模块表单/列表字段，详见页面配置 |
| storagePositionId | 存放位置 | 模块表单/列表字段，详见页面配置 |
| countUnit         | 计数单位 | 模块表单/列表字段，详见页面配置 |
| standardNum       | 标准数量 | 模块表单/列表字段，详见页面配置 |
| actualNum         | 实际数量 | 模块表单/列表字段，详见页面配置 |
| usableNum         | 可用数量 | 模块表单/列表字段，详见页面配置 |
| toolSituation     | 质量状况 | 模块表单/列表字段，详见页面配置 |
| toolManager       | 责任人   | 模块表单/列表字段，详见页面配置 |
| remark            | 备注     | 模块表单/列表字段，详见页面配置 |

---

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                                    | 关系说明 |
| ------------------------------------------- | -------- |
| 入库存管理（in_stock_management）           | 同组     |
| 物资管理（material_management）             | 同组     |
| 仓储位置管理（storage_position_management） | 同组     |
| 工具类型管理（tool_type_management）        | 同组     |

### 5.2 上游依赖 / 下游消费

- **上游**：监控设备（`monitor_equipment`）、备品备件管理（`spare_parts_management`）、用户及参数管理（`user`）。

---
