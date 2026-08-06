# 交接班记录（week_handover）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                                         |
| ------------------ | ---------------------------------------------------------------------------- |
| 模块名称（中文）   | 交接班记录                                                                   |
| 模块名称（英文）   | Week Handover                                                                |
| 所属 Group（中文） | 日常值班                                                                     |
| 所属 Group（英文） | Daily Duty                                                                   |
| Group ID           | `daily_duty`                                                                 |
| 菜单位置           | 配置管理平台 → 阵地维护管理 → 日常值班 → 交接班记录                          |
| 路由路径           | `/config_management/positional_management/week_handover`                     |
| 页面目录           | `src/pages/config_management/positional_management/daily_duty/week_handover` |

## 1. 模块定位与项目作用

周交接是综合信息平台中「日常值班」业务域下的功能模块，对应页面目录 `src/pages/config_management/positional_management/daily_duty/week_handover`。

在项目中的主要作用：

- 作为「配置管理平台 → 阵地维护管理 → 日常值班 → 周交接」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
- 通过本模块维护或消费的数据，可能被同业务域其他页面、报表、组态或流程能力引用。
- 具体能力以页面交互与接口清单为准；变更本模块配置/数据时，应评估对上下游模块的影响。

---

## 3. 属性字段说明

以下字段由页面代码启发式提取，用于快速了解主数据形态；若与线上表单不一致，以实际页面与接口契约为准。

| 字段名              | 中文含义 | 作用说明                        |
| ------------------- | -------- | ------------------------------- |
| positionName        | 交班时间 | 模块表单/列表字段，详见页面配置 |
| positionId          | 值班岗位 | 模块表单/列表字段，详见页面配置 |
| handoverTime        | 交班时间 | 模块表单/列表字段，详见页面配置 |
| receiveTime         | 接班时间 | 模块表单/列表字段，详见页面配置 |
| handoverPersonIds   | 交班人   | 模块表单/列表字段，详见页面配置 |
| handoverPersonNames | 交班人   | 模块表单/列表字段，详见页面配置 |
| receivePersonIds    | 接班人   | 模块表单/列表字段，详见页面配置 |
| receivePersonNames  | 接班人   | 模块表单/列表字段，详见页面配置 |
| remark              | 情况说明 | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

---

- 复制

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                            | 关系说明 |
| ----------------------------------- | -------- |
| 执勤交接（duty_handover）           | 同组     |
| 执勤information（duty_information） | 同组     |
| 执勤日志（duty_logs）               | 同组     |
| 执勤人员（duty_personnel）          | 同组     |
| 执勤计划（duty_plan）               | 同组     |
| 执勤设置（duty_setting）            | 同组     |
| 进入退出审批（entry_exit_approval） | 同组     |

### 5.2 上游依赖 / 下游消费

- **上游**：用户及参数管理（`user`）、阵地人员管理（`staff_management`）、基础数据（`basedata`）。

---
