# 场景管理（module_manage）知识库

> 上级模块索引：[user.md](./user.md) · 总索引：[README.md](./README.md) · 页面总表：[TOTAL-MODULE.md](./TOTAL-MODULE.md)

## 0. 路由与归属信息

| 项                 | 内容                                                    |
| ------------------ | ------------------------------------------------------- |
| 模块名称（中文）   | 场景管理                                                |
| 模块名称（英文）   | Module Manage                                           |
| 所属 Group（中文） | 用户及参数管理                                          |
| 所属 Group（英文） | User and Parameter Management                           |
| Group ID           | `user`                                                  |
| 菜单位置           | 配置管理平台 → 系统管理 → 用户及参数管理 → 场景管理     |
| 路由路径           | `/config_management/system/module_manage`               |
| 页面目录           | `src/pages/config_management/system/user/module_manage` |

## 1. 模块定位与项目作用

模块管理是综合信息平台中「用户及参数管理」业务域下的功能模块，对应页面目录 `src/pages/config_management/system/user/module_manage`。

在项目中的主要作用：

- 作为「配置管理平台 → 系统管理 → 用户及参数管理 → 模块管理」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
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

| 字段名                   | 中文含义                 | 作用说明                        |
| ------------------------ | ------------------------ | ------------------------------- |
| menuId                   | ID                       | 模块表单/列表字段，详见页面配置 |
| id                       | ID                       | 模块表单/列表字段，详见页面配置 |
| name                     | 模块名称                 | 模块表单/列表字段，详见页面配置 |
| path                     | 模块键值                 | 模块表单/列表字段，详见页面配置 |
| meta                     | 元数据                   | 模块表单/列表字段，详见页面配置 |
| remark                   | 描述                     | 模块表单/列表字段，详见页面配置 |
| index                    | serialNumber             | 模块表单/列表字段，详见页面配置 |
| exportStatus             | fileExportStatus         | 模块表单/列表字段，详见页面配置 |
| module_managediagnostic  | module_managediagnostic  | 模块表单/列表字段，详见页面配置 |
| export                   | export                   | 模块表单/列表字段，详见页面配置 |
| sceneSetting             | sceneSetting             | 模块表单/列表字段，详见页面配置 |
| configFileManagementJump | configFileManagementJump | 模块表单/列表字段，详见页面配置 |
| configBatchExport        | configBatchExport        | 模块表单/列表字段，详见页面配置 |
| conventionalBatchImport  | conventionalBatchImport  | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

- 新建/新增
- 编辑
- 删除
- 详情回填
- 导出
- 导入
- 左侧树筛选
- 启用/停用
- 分页查询

---

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                  | 关系说明                                           |
| ------------------------- | -------------------------------------------------- |
| 文件分类（file_category） | 同级功能模块，可共同构成「用户及参数管理」业务能力 |
| 菜单管理（menu_manage）   | 同级功能模块，可共同构成「用户及参数管理」业务能力 |
| 组织机构（organization）  | 同级功能模块，可共同构成「用户及参数管理」业务能力 |
| 角色授权（role_auth）     | 同级功能模块，可共同构成「用户及参数管理」业务能力 |
| 角色管理（role_manage）   | 同级功能模块，可共同构成「用户及参数管理」业务能力 |
| 用户组（user_group）      | 同级功能模块，可共同构成「用户及参数管理」业务能力 |
| 用户管理（user_manage）   | 同级功能模块，可共同构成「用户及参数管理」业务能力 |

### 5.2 上游依赖 / 下游消费

- **上游**：本模块属于权限与账号体系本身；上游主要为组织机构树（同属用户及参数管理）及系统运维中的数据源可用性。字典表可能为表单枚举提供选项。
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

本模块（`module_manage`）位于 `src/pages/config_management/system/user/module_manage`，归属「用户及参数管理」。它负责「模块管理」相关业务的页面交互与数据读写。维护本模块时，请同步关注接口契约、字段语义及与兄弟模块的数据一致性。

---

## 8. 接口清单

以下接口由本模块页面代码直接或通过 `@/services` Controller 调用，参数与响应 Schema 来自平台 OpenAPI（若可匹配）。

### 8.1 validateMouduleSceneDevices

| 项       | 内容                                           |
| -------- | ---------------------------------------------- |
| 接口路径 | `/hmi/checkHmiDevInfo`                         |
| 请求方法 | `GET`                                          |
| 前端封装 | `SystemController.validateMouduleSceneDevices` |
| 作用说明 | 见模块业务逻辑                                 |

_未在平台 OpenAPI 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---

### 8.2 uploadHmiJson

| 项       | 内容                             |
| -------- | -------------------------------- |
| 接口路径 | `/hmiFile/uploadHmiJson`         |
| 请求方法 | `POST`                           |
| 前端封装 | `SystemController.uploadHmiJson` |
| 作用说明 | 见模块业务逻辑                   |

_未在平台 OpenAPI 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---

### 8.3 修改组态模块配置

| 项          | 内容                       |
| ----------- | -------------------------- |
| 接口路径    | `/hmi/editHmi`             |
| 请求方法    | `POST`                     |
| 前端封装    | `SystemController.editHmi` |
| Swagger Tag | hmiApi                     |
| 作用说明    | 修改组态模块配置           |

**请求参数（Body）：**

| 字段     | 类型      | 说明 |
| -------- | --------- | ---- |
| `id`     | `integer` |      |
| `name`   | `string`  |      |
| `remark` | `string`  |      |
| `path`   | `string`  |      |
| `meta`   | `string`  |      |
| `type`   | `string`  |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.4 添加组态模块配置

| 项          | 内容                      |
| ----------- | ------------------------- |
| 接口路径    | `/hmi/addHmi`             |
| 请求方法    | `POST`                    |
| 前端封装    | `SystemController.addHmi` |
| Swagger Tag | hmiApi                    |
| 作用说明    | 添加组态模块配置          |

**请求参数（Body）：**

| 字段     | 类型     | 说明 |
| -------- | -------- | ---- |
| `name`   | `string` |      |
| `remark` | `string` |      |
| `path`   | `string` |      |
| `meta`   | `string` |      |
| `type`   | `string` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.5 获取组态模块配置列表

| 项          | 内容                          |
| ----------- | ----------------------------- |
| 接口路径    | `/hmi/getHmiList`             |
| 请求方法    | `POST`                        |
| 前端封装    | `SystemController.getHmiList` |
| Swagger Tag | hmiApi                        |
| 作用说明    | 获取组态模块配置列表          |

**请求参数（Body）：**

| 字段   | 类型      | 说明     |
| ------ | --------- | -------- |
| `name` | `string`  | 模块名称 |
| `page` | `integer` |          |
| `size` | `integer` |          |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.6 删除组态模块配置

| 项          | 内容                      |
| ----------- | ------------------------- |
| 接口路径    | `/hmi/delHmi`             |
| 请求方法    | `POST`                    |
| 前端封装    | `SystemController.delHmi` |
| Swagger Tag | hmiApi                    |
| 作用说明    | 删除组态模块配置          |

**请求参数（Body）：**

| 字段 | 类型      | 说明 |
| ---- | --------- | ---- |
| `id` | `integer` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.7 getAdminHmi

| 项       | 内容                           |
| -------- | ------------------------------ |
| 接口路径 | `/hmi/getAdminHmi`             |
| 请求方法 | `POST`                         |
| 前端封装 | `SystemController.getAdminHmi` |
| 作用说明 | 见模块业务逻辑                 |

_未在平台 OpenAPI 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---

### 8.8 获取组态模块配置

| 项          | 内容                    |
| ----------- | ----------------------- |
| 接口路径    | `/hmi/getHmi`           |
| 请求方法    | `POST`                  |
| 前端封装    | `PageController.getHmi` |
| Swagger Tag | hmiApi                  |
| 作用说明    | 获取组态模块配置        |

**请求参数（Body）：**

| 字段 | 类型      | 说明 |
| ---- | --------- | ---- |
| `id` | `integer` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.9 getFileByPath

| 项       | 内容                             |
| -------- | -------------------------------- |
| 接口路径 | `未知`                           |
| 请求方法 | `未知`                           |
| 前端封装 | `SystemController.getFileByPath` |
| 作用说明 | 见模块业务逻辑                   |

_未在平台 OpenAPI 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---

### 8.10 获取菜单树

| 项          | 内容                           |
| ----------- | ------------------------------ |
| 接口路径    | `/menu/getMenuTree`            |
| 请求方法    | `POST`                         |
| 前端封装    | `SystemController.getMenuTree` |
| Swagger Tag | menuManagementApi              |
| 作用说明    | 获取菜单树                     |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---
