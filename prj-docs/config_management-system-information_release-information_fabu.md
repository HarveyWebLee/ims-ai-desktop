# 信息发布（information_fabu）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                                      |
| ------------------ | ------------------------------------------------------------------------- |
| 模块名称（中文）   | 信息发布                                                                  |
| 模块名称（英文）   | Information Fabu                                                          |
| 所属 Group（中文） | 信息发布                                                                  |
| 所属 Group（英文） | Information Release                                                       |
| Group ID           | `information_release`                                                     |
| 菜单位置           | 配置管理平台 → 系统管理 → 信息发布 → 信息发布                             |
| 路由路径           | `/config_management/system/information_fabu`                              |
| 页面目录           | `src/pages/config_management/system/information_release/information_fabu` |

## 1. 模块定位与项目作用

信息发布执行是综合信息平台中「信息发布」业务域下的功能模块，对应页面目录 `src/pages/config_management/system/information_release/information_fabu`。

在项目中的主要作用：

- 作为「配置管理平台 → 系统管理 → 信息发布 → 信息发布执行」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
- 通过本模块维护或消费的数据，可能被同业务域其他页面、报表、组态或流程能力引用。
- 具体能力以页面交互与接口清单为准；变更本模块配置/数据时，应评估对上下游模块的影响。

---

## 3. 属性字段说明

以下字段由页面代码启发式提取，用于快速了解主数据形态；若与线上表单不一致，以实际页面与接口契约为准。

| 字段名             | 中文含义    | 作用说明                        |
| ------------------ | ----------- | ------------------------------- |
| handoverSupervisor | 交班值班员1 | 模块表单/列表字段，详见页面配置 |
| handDutyPerson1    | 交班值班员2 | 模块表单/列表字段，详见页面配置 |
| handDutyPerson2    | 交班值班员3 | 模块表单/列表字段，详见页面配置 |
| handDutyPerson3    | 交班值班员4 | 模块表单/列表字段，详见页面配置 |
| takeoverSupervisor | 接班值班员1 | 模块表单/列表字段，详见页面配置 |
| takeDutyPerson1    | 接班值班员2 | 模块表单/列表字段，详见页面配置 |
| takeDutyPerson2    | 接班值班员3 | 模块表单/列表字段，详见页面配置 |
| takeDutyPerson3    | 接班值班员4 | 模块表单/列表字段，详见页面配置 |
| handDutyPerson4    | 交班值班员4 | 模块表单/列表字段，详见页面配置 |
| takeDutyPerson4    | 接班值班员4 | 模块表单/列表字段，详见页面配置 |
| handoverTime       | 交接班时间  | 模块表单/列表字段，详见页面配置 |
| handoverSituation  | 交接班情况  | 模块表单/列表字段，详见页面配置 |
| remark             | 备注        | 模块表单/列表字段，详见页面配置 |

---

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                                  | 关系说明 |
| ----------------------------------------- | -------- |
| 执勤管理（duty_management）               | 同组     |
| information管理（information_management） | 同组     |

### 5.2 上游依赖 / 下游消费

- **上游**：用户及参数管理（`user`）。

---
