# 数据备份（data_backup）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                           |
| ------------------ | -------------------------------------------------------------- |
| 模块名称（中文）   | 数据备份                                                       |
| 模块名称（英文）   | Data Backup                                                    |
| 所属 Group（中文） | 系统运维                                                       |
| 所属 Group（英文） | System DevOps                                                  |
| Group ID           | `system_devops`                                                |
| 菜单位置           | 配置管理平台 → 系统管理 → 系统运维 → 数据备份                  |
| 路由路径           | `/config_management/system/system_devops/data_backup`          |
| 页面目录           | `src/pages/config_management/system/system_devops/data_backup` |

## 1. 模块定位与项目作用

数据备份是综合信息平台中「系统运维」业务域下的功能模块，对应页面目录 `src/pages/config_management/system/system_devops/data_backup`。

在项目中的主要作用：

- 作为「配置管理平台 → 系统管理 → 系统运维 → 数据备份」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
- 通过本模块维护或消费的数据，可能被同业务域其他页面、报表、组态或流程能力引用。
- 具体能力以页面交互与接口清单为准；变更本模块配置/数据时，应评估对上下游模块的影响。

---

## 2. 页面与交互结构

页面结构以该目录下 `index.tsx` / `constants.tsx` 实现为准，常见为配置管理类「查询列表 + 表单弹窗/抽屉」或「左树右表」布局。

### 2.1 列表与查询

- 支持条件查询与列表展示（若页面启用了表格组件）。
- 树筛选、分页、导入导出等能力取决于本模块是否接入对应通用配置。

### 2.2 表单与编辑

- 新增/编辑通过表单提交，字段见「属性字段说明」。
- 校验规则、联动逻辑以 `constants` 与表单配置为准。

---

## 3. 属性字段说明

以下字段由页面代码启发式提取，用于快速了解主数据形态；若与线上表单不一致，以实际页面与接口契约为准。

| 字段名      | 中文含义   | 作用说明                        |
| ----------- | ---------- | ------------------------------- |
| filePath    | backupItem | 模块表单/列表字段，详见页面配置 |
| backupType  | backupItem | 模块表单/列表字段，详见页面配置 |
| backupModel | backupMode | 模块表单/列表字段，详见页面配置 |
| backupTime  | backupTime | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

- 编辑
- 导出
- 导入
- 启用/停用
- 分页查询

---

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                             | 关系说明                                     |
| ------------------------------------ | -------------------------------------------- |
| 数据源管理（data-source-management） | 同级功能模块，可共同构成「系统运维」业务能力 |

### 5.2 上游依赖 / 下游消费

- **上游**：基础数据、字典、组织/设备主数据、登录权限等（按本模块实际选型接口而定）。
- **下游**：引用本模块数据的统计、告警、组态、流程或其他业务页（以全库引用为准）。

---

## 6. 关键业务规则与注意事项

1. 操作前确认当前用户具备对应菜单与按钮权限。
2. 删除、导入、批量变更等操作可能影响下游运行态数据，执行前应确认范围。
3. 若模块涉及驱动/采集类配置，变更后可能需要在数采或相关服务侧刷新配置后生效。
4. 接口入参以 Swagger 与前端封装为准，注意必填项与枚举值。
5. 国际化环境下，界面文案以 `src/locales` 配置为准。

---

## 7. 总结

本模块（`data_backup`）位于 `src/pages/config_management/system/system_devops/data_backup`，归属「系统运维」。它负责「数据备份」相关业务的页面交互与数据读写。维护本模块时，请同步关注接口契约、字段语义及与兄弟模块的数据一致性。

---

## 8. 接口清单

以下接口由本模块页面代码直接或通过 `@/services` Controller 调用，参数与响应 Schema 来自 `swaggerApi.json`（若可匹配）。

### 8.1 setDataBackupNodeInfo

| 项       | 内容                                         |
| -------- | -------------------------------------------- |
| 接口路径 | `未知`                                       |
| 请求方法 | `未知`                                       |
| 前端封装 | `DataBackupController.setDataBackupNodeInfo` |
| 作用说明 | 见模块业务逻辑                               |

_未在 `swaggerApi.json` 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---

### 8.2 checkDataBackupNode

| 项       | 内容                                       |
| -------- | ------------------------------------------ |
| 接口路径 | `未知`                                     |
| 请求方法 | `未知`                                     |
| 前端封装 | `DataBackupController.checkDataBackupNode` |
| 作用说明 | 见模块业务逻辑                             |

_未在 `swaggerApi.json` 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---

### 8.3 getDataBackupNodeInfo

| 项       | 内容                                         |
| -------- | -------------------------------------------- |
| 接口路径 | `未知`                                       |
| 请求方法 | `未知`                                       |
| 前端封装 | `DataBackupController.getDataBackupNodeInfo` |
| 作用说明 | 见模块业务逻辑                               |

_未在 `swaggerApi.json` 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---

### 8.4 getDataBackupConfig

| 项       | 内容                                       |
| -------- | ------------------------------------------ |
| 接口路径 | `未知`                                     |
| 请求方法 | `未知`                                     |
| 前端封装 | `DataBackupController.getDataBackupConfig` |
| 作用说明 | 见模块业务逻辑                             |

_未在 `swaggerApi.json` 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---

### 8.5 getBackupTypes

| 项       | 内容                                    |
| -------- | --------------------------------------- |
| 接口路径 | `/remoteBackup/getBackupTypes`          |
| 请求方法 | `POST`                                  |
| 前端封装 | `data-backup-controller.getBackupTypes` |
| baseURL  | `/api/devops`                           |
| 作用说明 | 见模块业务逻辑                          |

_未在 `swaggerApi.json` 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---

### 8.6 getDataBackupRecordList

| 项       | 内容                                           |
| -------- | ---------------------------------------------- |
| 接口路径 | `未知`                                         |
| 请求方法 | `未知`                                         |
| 前端封装 | `DataBackupController.getDataBackupRecordList` |
| 作用说明 | 见模块业务逻辑                                 |

_未在 `swaggerApi.json` 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---

### 8.7 delBackupRecord

| 项       | 内容                                   |
| -------- | -------------------------------------- |
| 接口路径 | `未知`                                 |
| 请求方法 | `未知`                                 |
| 前端封装 | `DataBackupController.delBackupRecord` |
| 作用说明 | 见模块业务逻辑                         |

_未在 `swaggerApi.json` 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---

### 8.8 setDataBackupConfig

| 项       | 内容                                       |
| -------- | ------------------------------------------ |
| 接口路径 | `未知`                                     |
| 请求方法 | `未知`                                     |
| 前端封装 | `DataBackupController.setDataBackupConfig` |
| 作用说明 | 见模块业务逻辑                             |

_未在 `swaggerApi.json` 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---

### 8.9 manualBackupData

| 项       | 内容                                    |
| -------- | --------------------------------------- |
| 接口路径 | `未知`                                  |
| 请求方法 | `未知`                                  |
| 前端封装 | `DataBackupController.manualBackupData` |
| 作用说明 | 见模块业务逻辑                          |

_未在 `swaggerApi.json` 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---
