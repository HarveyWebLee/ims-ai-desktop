# 计量记录管理（measurement_record_management）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                                                                                  |
| ------------------ | --------------------------------------------------------------------------------------------------------------------- |
| 模块名称（中文）   | 计量记录管理                                                                                                          |
| 模块名称（英文）   | Measurement Record Management                                                                                         |
| 所属 Group（中文） | 计量校验管理                                                                                                          |
| 所属 Group（英文） | Metrology Verification Management                                                                                     |
| Group ID           | `measurement_verification_management`                                                                                 |
| 菜单位置           | 配置管理平台 → 阵地维护管理 → 计量校验管理 → 计量记录管理                                                             |
| 路由路径           | `/config_management/positional_management/measurement_record_management`                                              |
| 页面目录           | `src/pages/config_management/positional_management/measurement_verification_management/measurement_record_management` |

## 1. 模块定位与项目作用

计量记录管理是综合信息平台中「计量校验管理」业务域下的功能模块，对应页面目录 `src/pages/config_management/positional_management/measurement_verification_management/measurement_record_management`。

在项目中的主要作用：

- 作为「配置管理平台 → 阵地维护管理 → 计量校验管理 → 计量记录管理」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
- 通过本模块维护或消费的数据，可能被同业务域其他页面、报表、组态或流程能力引用。
- 具体能力以页面交互与接口清单为准；变更本模块配置/数据时，应评估对上下游模块的影响。

---

## 3. 属性字段说明

以下字段由页面代码启发式提取，用于快速了解主数据形态；若与线上表单不一致，以实际页面与接口契约为准。

| 字段名               | 中文含义 | 作用说明                        |
| -------------------- | -------- | ------------------------------- |
| meteringCategory     | 计量型号 | 模块表单/列表字段，详见页面配置 |
| meteringOrganization | 计量人员 | 模块表单/列表字段，详见页面配置 |
| meteringObject       | 计量对象 | 模块表单/列表字段，详见页面配置 |
| meteringCode         | 计量编号 | 模块表单/列表字段，详见页面配置 |
| meteringModel        | 计量型号 | 模块表单/列表字段，详见页面配置 |
| meteringTime         | 计量时间 | 模块表单/列表字段，详见页面配置 |
| meteringValidTime    | 有效时间 | 模块表单/列表字段，详见页面配置 |
| meteringPerson       | 计量人员 | 模块表单/列表字段，详见页面配置 |
| meteringResult       | 计量结果 | 模块表单/列表字段，详见页面配置 |

---

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                                      | 关系说明 |
| --------------------------------------------- | -------- |
| 计量对象管理（measurement_object_management） | 同组     |

### 5.2 上游依赖 / 下游消费

- **上游**：用户及参数管理（`user`）。

---
