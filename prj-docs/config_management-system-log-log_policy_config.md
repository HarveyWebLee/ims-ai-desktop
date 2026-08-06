# 日志策略配置（log_policy_config）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                       |
| ------------------ | ---------------------------------------------------------- |
| 模块名称（中文）   | 日志策略配置                                               |
| 模块名称（英文）   | Log Policy Config                                          |
| 所属 Group（中文） | 日志管理                                                   |
| 所属 Group（英文） | Log Management                                             |
| Group ID           | `log`                                                      |
| 菜单位置           | 配置管理平台 → 系统管理 → 日志管理 → 日志策略配置          |
| 路由路径           | `/config_management/system/log_policy_config`              |
| 页面目录           | `src/pages/config_management/system/log/log_policy_config` |

## 1. 模块定位与项目作用

日志策略配置是综合信息平台中「日志管理」业务域下的功能模块，对应页面目录 `src/pages/config_management/system/log/log_policy_config`。

在项目中的主要作用：

- 作为「配置管理平台 → 系统管理 → 日志管理 → 日志策略配置」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
- 通过本模块维护或消费的数据，可能被同业务域其他页面、报表、组态或流程能力引用。
- 具体能力以页面交互与接口清单为准；变更本模块配置/数据时，应评估对上下游模块的影响。

---

## 3. 属性字段说明

以下字段由页面代码启发式提取，用于快速了解主数据形态；若与线上表单不一致，以实际页面与接口契约为准。

| 字段名             | 中文含义         | 作用说明                        |
| ------------------ | ---------------- | ------------------------------- |
| logModule          | 日志模块         | 模块表单/列表字段，详见页面配置 |
| strategyId         | 策略ID           | 模块表单/列表字段，详见页面配置 |
| recordPeriodValue  | 日志记录周期     | 模块表单/列表字段，详见页面配置 |
| recordPeriodUnit   | 日志记录周期单位 | 模块表单/列表字段，详见页面配置 |
| saveTimeValue      | 日志保存时间     | 模块表单/列表字段，详见页面配置 |
| saveTimeUnit       | 日志保存时间单位 | 模块表单/列表字段，详见页面配置 |
| recordFrequencySec | 日志记录频率     | 模块表单/列表字段，详见页面配置 |

---

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                                | 关系说明 |
| --------------------------------------- | -------- |
| 业务应用log（business_application_log） | 同组     |
| 设备操作（equipment_operation）         | 同组     |
| log审计（log_audit）                    | 同组     |
| 网络安全log（network_security_log）     | 同组     |
| 系统门禁（system_access）               | 同组     |
| 系统操作（system_operation）            | 同组     |
| 系统运行log（system_runtime_log）       | 同组     |
| 用户行为log（user_behavior_log）        | 同组     |

### 5.2 上游依赖 / 下游消费

- **上游**：用户及参数管理（`user`）。

---
