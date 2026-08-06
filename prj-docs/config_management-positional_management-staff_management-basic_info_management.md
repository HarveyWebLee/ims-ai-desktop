# 基本信息管理（basic_info_management）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                                                       |
| ------------------ | ------------------------------------------------------------------------------------------ |
| 模块名称（中文）   | 基本信息管理                                                                               |
| 模块名称（英文）   | Basic Info Management                                                                      |
| 所属 Group（中文） | 阵地人员管理                                                                               |
| 所属 Group（英文） | Position Staff Management                                                                  |
| Group ID           | `staff_management`                                                                         |
| 菜单位置           | 配置管理平台 → 阵地维护管理 → 阵地人员管理 → 基本信息管理                                  |
| 路由路径           | `/config_management/positional_management/basic_info_management`                           |
| 页面目录           | `src/pages/config_management/positional_management/staff_management/basic_info_management` |

## 1. 模块定位与项目作用

基础信息管理是综合信息平台中「阵地人员管理」业务域下的功能模块，对应页面目录 `src/pages/config_management/positional_management/staff_management/basic_info_management`。

在项目中的主要作用：

- 作为「配置管理平台 → 阵地维护管理 → 阵地人员管理 → 基础信息管理」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
- 通过本模块维护或消费的数据，可能被同业务域其他页面、报表、组态或流程能力引用。
- 具体能力以页面交互与接口清单为准；变更本模块配置/数据时，应评估对上下游模块的影响。

---

## 3. 属性字段说明

以下字段由页面代码启发式提取，用于快速了解主数据形态；若与线上表单不一致，以实际页面与接口契约为准。

| 字段名               | 中文含义 | 作用说明                        |
| -------------------- | -------- | ------------------------------- |
| personName           | 人员名称 | 模块表单/列表字段，详见页面配置 |
| militaryRankId       | 军衔     | 模块表单/列表字段，详见页面配置 |
| militaryRankName     | 军衔     | 模块表单/列表字段，详见页面配置 |
| militaryPositionId   | 职务     | 模块表单/列表字段，详见页面配置 |
| militaryPositionName | 职务     | 模块表单/列表字段，详见页面配置 |
| majorId              | 专业     | 模块表单/列表字段，详见页面配置 |
| majorName            | 专业     | 模块表单/列表字段，详见页面配置 |
| technicalLevelId     | 技能等级 | 模块表单/列表字段，详见页面配置 |
| technicalLevelName   | 技能等级 | 模块表单/列表字段，详见页面配置 |

---

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                                                | 关系说明 |
| ------------------------------------------------------- | -------- |
| 考核结果（assessment_results）                          | 同组     |
| 人员information统计（personnel_information_statistics） | 同组     |
| 资质证书（qualification_certificate）                   | 同组     |
| 任务情况（task_situation）                              | 同组     |
| 培训情况（training_situation）                          | 同组     |
| 工作经历（work_experience）                             | 同组     |

### 5.2 上游依赖 / 下游消费

- **上游**：用户及参数管理（`user`）、字典表（`dic_table`）、基础数据（`basedata`）。

---
