# 物资移交单（transfer_management_record）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                                                                       |
| ------------------ | ---------------------------------------------------------------------------------------------------------- |
| 模块名称（中文）   | 物资移交单                                                                                                 |
| 模块名称（英文）   | Transfer Management Record                                                                                 |
| 所属 Group（中文） | 物资移交管理                                                                                               |
| 所属 Group（英文） | Transfer Management Service                                                                                |
| Group ID           | `transfer_management_service`                                                                              |
| 菜单位置           | 配置管理平台 → 阵地维护管理 → 物资移交管理 → 物资移交单                                                    |
| 路由路径           | `/config_management/positional_management/transfer_management_record`                                      |
| 页面目录           | `src/pages/config_management/positional_management/transfer_management_service/transfer_management_record` |

## 1. 模块定位与项目作用

移交管理记录是综合信息平台中「物资移交管理」业务域下的功能模块，对应页面目录 `src/pages/config_management/positional_management/transfer_management_service/transfer_management_record`。

在项目中的主要作用：

- 作为「配置管理平台 → 阵地维护管理 → 物资移交管理 → 移交管理记录」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
- 通过本模块维护或消费的数据，可能被同业务域其他页面、报表、组态或流程能力引用。
- 具体能力以页面交互与接口清单为准；变更本模块配置/数据时，应评估对上下游模块的影响。

---

## 3. 属性字段说明

以下字段由页面代码启发式提取，用于快速了解主数据形态；若与线上表单不一致，以实际页面与接口契约为准。

| 字段名           | 中文含义     | 作用说明                        |
| ---------------- | ------------ | ------------------------------- |
| handoverCode     | 移交单号     | 模块表单/列表字段，详见页面配置 |
| handoverPerson   | 交付人       | 模块表单/列表字段，详见页面配置 |
| acceptPerson     | 接收人       | 模块表单/列表字段，详见页面配置 |
| invigilatePerson | 监交人       | 模块表单/列表字段，详见页面配置 |
| timeRange        | 交接时间范围 | 模块表单/列表字段，详见页面配置 |
| handoverTime     | 交接时间     | 模块表单/列表字段，详见页面配置 |
| handoverPic      | 移交物资附件 | 模块表单/列表字段，详见页面配置 |
| remark           | 备注         | 模块表单/列表字段，详见页面配置 |
| file             | file         | 模块表单/列表字段，详见页面配置 |

---

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

暂无明显同级兄弟模块，或同级目录未识别为独立页面。

### 5.2 上游依赖 / 下游消费

- **上游**：监控设备（`monitor_equipment`）、备品备件管理（`spare_parts_management`）、工具资料（`tool_information`）、用户及参数管理（`user`）。

---
