# 用户行为日志（user_behavior_log）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                       |
| ------------------ | ---------------------------------------------------------- |
| 模块名称（中文）   | 用户行为日志                                               |
| 模块名称（英文）   | User Behavior Log                                          |
| 所属 Group（中文） | 日志管理                                                   |
| 所属 Group（英文） | Log Management                                             |
| Group ID           | `log`                                                      |
| 菜单位置           | 配置管理平台 → 系统管理 → 日志管理 → 用户行为日志          |
| 路由路径           | `/config_management/system/user_behavior_log`              |
| 页面目录           | `src/pages/config_management/system/log/user_behavior_log` |

## 1. 模块定位与项目作用

用户行为日志是综合信息平台中「日志管理」业务域下的功能模块，对应页面目录 `src/pages/config_management/system/log/user_behavior_log`。

在项目中的主要作用：

- 作为「配置管理平台 → 系统管理 → 日志管理 → 用户行为日志」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
- 通过本模块维护或消费的数据，可能被同业务域其他页面、报表、组态或流程能力引用。
- 具体能力以页面交互与接口清单为准；变更本模块配置/数据时，应评估对上下游模块的影响。

---

## 4. 与其他功能模块的关系

### 4.1 同目录兄弟模块

| 关联模块                                | 关系说明 |
| --------------------------------------- | -------- |
| 业务应用log（business_application_log） | 同组     |
| 设备操作（equipment_operation）         | 同组     |
| log审计（log_audit）                    | 同组     |
| log策略配置（log_policy_config）        | 同组     |
| 网络安全log（network_security_log）     | 同组     |
| 系统门禁（system_access）               | 同组     |
| 系统操作（system_operation）            | 同组     |
| 系统运行log（system_runtime_log）       | 同组     |

### 4.2 上游依赖 / 下游消费

- **上游**：用户及参数管理（`user`）。

---
