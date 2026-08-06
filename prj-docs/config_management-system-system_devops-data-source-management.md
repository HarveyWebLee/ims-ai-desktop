# 数据迁移（data-source-management）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                                      |
| ------------------ | ------------------------------------------------------------------------- |
| 模块名称（中文）   | 数据迁移                                                                  |
| 模块名称（英文）   | Data Source Management                                                    |
| 所属 Group（中文） | 系统运维                                                                  |
| 所属 Group（英文） | System DevOps                                                             |
| Group ID           | `system_devops`                                                           |
| 菜单位置           | 配置管理平台 → 系统管理 → 系统运维 → 数据迁移                             |
| 路由路径           | `/config_management/system/data-source-management`                        |
| 页面目录           | `src/pages/config_management/system/system_devops/data-source-management` |

## 1. 模块定位与项目作用

数据源管理是综合信息平台中「系统运维」业务域下的功能模块，对应页面目录 `src/pages/config_management/system/system_devops/data-source-management`。

在项目中的主要作用：

- 作为「配置管理平台 → 系统管理 → 系统运维 → 数据源管理」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
- 通过本模块维护或消费的数据，可能被同业务域其他页面、报表、组态或流程能力引用。
- 具体能力以页面交互与接口清单为准；变更本模块配置/数据时，应评估对上下游模块的影响。

---

## 3. 功能清单

---

- 分页查询

## 4. 与其他功能模块的关系

### 4.1 同目录兄弟模块

| 关联模块                | 关系说明 |
| ----------------------- | -------- |
| 数据备份（data_backup） | 同组     |

### 4.2 上游依赖 / 下游消费

- **上游**：事件配置（`event_config`）、用户及参数管理（`user`）。

---
