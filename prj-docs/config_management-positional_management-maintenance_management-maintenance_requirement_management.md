# 保养要求管理（maintenance_requirement_management）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                                                                          |
| ------------------ | ------------------------------------------------------------------------------------------------------------- |
| 模块名称（中文）   | 保养要求管理                                                                                                  |
| 模块名称（英文）   | Maintenance Requirement Management                                                                            |
| 所属 Group（中文） | 维护保养管理                                                                                                  |
| 所属 Group（英文） | Maintenance Management                                                                                        |
| Group ID           | `maintenance_management`                                                                                      |
| 菜单位置           | 配置管理平台 → 阵地维护管理 → 维护保养管理 → 保养要求管理                                                     |
| 路由路径           | `/config_management/positional_management/maintenance_requirement_management`                                 |
| 页面目录           | `src/pages/config_management/positional_management/maintenance_management/maintenance_requirement_management` |

## 1. 模块定位与项目作用

保养需求管理是综合信息平台中「维护保养管理」业务域下的功能模块，对应页面目录 `src/pages/config_management/positional_management/maintenance_management/maintenance_requirement_management`。

在项目中的主要作用：

- 作为「配置管理平台 → 阵地维护管理 → 维护保养管理 → 保养需求管理」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
- 通过本模块维护或消费的数据，可能被同业务域其他页面、报表、组态或流程能力引用。
- 具体能力以页面交互与接口清单为准；变更本模块配置/数据时，应评估对上下游模块的影响。

---

## 3. 属性字段说明

以下字段由页面代码启发式提取，用于快速了解主数据形态；若与线上表单不一致，以实际页面与接口契约为准。

| 字段名          | 中文含义        | 作用说明                        |
| --------------- | --------------- | ------------------------------- |
| name            | 名称            | 模块表单/列表字段，详见页面配置 |
| remark          | 备注            | 模块表单/列表字段，详见页面配置 |
| requireName     | requireName     | 模块表单/列表字段，详见页面配置 |
| upkeepCode      | upkeepCode      | 模块表单/列表字段，详见页面配置 |
| upkeepWorkflow  | upkeepWorkflow  | 模块表单/列表字段，详见页面配置 |
| upkeepTechnique | upkeepTechnique | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

---

- 分页查询

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                                             | 关系说明 |
| ---------------------------------------------------- | -------- |
| maintenance方案管理（maintenance_scheme_management） | 同组     |
| maintenance任务管理（maintenance_task_management）   | 同组     |

### 5.2 上游依赖 / 下游消费

- **上游**：用户及参数管理（`user`）。

---
