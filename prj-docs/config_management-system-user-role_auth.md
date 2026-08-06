# 角色授权（role_auth）知识库

> 上级模块索引：[user.md](./user.md) · 总索引：[README.md](./README.md) · 页面总表：[TOTAL-MODULE.md](./TOTAL-MODULE.md)

## 0. 路由与归属信息

| 项                 | 内容                                                |
| ------------------ | --------------------------------------------------- |
| 模块名称（中文）   | 角色授权                                            |
| 模块名称（英文）   | Role Auth                                           |
| 所属 Group（中文） | 用户及参数管理                                      |
| 所属 Group（英文） | User and Parameter Management                       |
| Group ID           | `user`                                              |
| 菜单位置           | 配置管理平台 → 系统管理 → 用户及参数管理 → 角色授权 |
| 路由路径           | `/config_management/system/role_auth`               |
| 页面目录           | `src/pages/config_management/system/user/role_auth` |

## 1. 模块定位与项目作用

角色授权是综合信息平台中「用户及参数管理」业务域下的功能模块，对应页面目录 `src/pages/config_management/system/user/role_auth`。

在项目中的主要作用：

- 作为「配置管理平台 → 系统管理 → 用户及参数管理 → 角色授权」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
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

| 字段名     | 中文含义 | 作用说明                        |
| ---------- | -------- | ------------------------------- |
| apiAuth    | 接口授权 | 模块表单/列表字段，详见页面配置 |
| deviceAuth | 设备授权 | 模块表单/列表字段，详见页面配置 |
| menuAuth   | 菜单授权 | 模块表单/列表字段，详见页面配置 |
| fileAuth   | 文件授权 | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

- 新建/新增
- 导出
- 导入
- 左侧树筛选

---

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                  | 关系说明                                           |
| ------------------------- | -------------------------------------------------- |
| 文件分类（file_category） | 同级功能模块，可共同构成「用户及参数管理」业务能力 |
| 菜单管理（menu_manage）   | 同级功能模块，可共同构成「用户及参数管理」业务能力 |
| 模块管理（module_manage） | 同级功能模块，可共同构成「用户及参数管理」业务能力 |
| 组织机构（organization）  | 同级功能模块，可共同构成「用户及参数管理」业务能力 |
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

本模块（`role_auth`）位于 `src/pages/config_management/system/user/role_auth`，归属「用户及参数管理」。它负责「角色授权」相关业务的页面交互与数据读写。维护本模块时，请同步关注接口契约、字段语义及与兄弟模块的数据一致性。

---

## 8. 接口清单

以下接口由本模块页面代码直接或通过 `@/services` Controller 调用，参数与响应 Schema 来自平台 OpenAPI（若可匹配）。

### 8.1 获取角色数组

| 项          | 内容                        |
| ----------- | --------------------------- |
| 接口路径    | `/role/getRoles`            |
| 请求方法    | `POST`                      |
| 前端封装    | `SystemController.getRoles` |
| Swagger Tag | roleManagementApi           |
| 作用说明    | 获取角色数组                |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.2 分配权限（批量）

| 项          | 内容                         |
| ----------- | ---------------------------- |
| 接口路径    | `/role/allotPerm`            |
| 请求方法    | `POST`                       |
| 前端封装    | `SystemController.allotPerm` |
| Swagger Tag | roleManagementApi            |
| 作用说明    | 分配权限（批量）             |

**请求参数（Body）：**

| 字段      | 类型             | 说明 |
| --------- | ---------------- | ---- |
| `id`      | `integer`        |      |
| `permIds` | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.3 分配设备权限（批量）

| 项          | 内容                           |
| ----------- | ------------------------------ |
| 接口路径    | `/role/allotDevice`            |
| 请求方法    | `POST`                         |
| 前端封装    | `SystemController.allotDevice` |
| Swagger Tag | roleManagementApi              |
| 作用说明    | 分配设备权限（批量）           |

**请求参数（Body）：**

| 字段        | 类型             | 说明 |
| ----------- | ---------------- | ---- |
| `id`        | `integer`        |      |
| `deviceIds` | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.4 分配菜单权限（批量）

| 项          | 内容                         |
| ----------- | ---------------------------- |
| 接口路径    | `/role/allotMenu`            |
| 请求方法    | `POST`                       |
| 前端封装    | `SystemController.allotMenu` |
| Swagger Tag | roleManagementApi            |
| 作用说明    | 分配菜单权限（批量）         |

**请求参数（Body）：**

| 字段      | 类型             | 说明 |
| --------- | ---------------- | ---- |
| `id`      | `integer`        |      |
| `menuIds` | `array<integer>` |      |
| `halfIds` | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.5 分配文件分类

| 项          | 内容                                 |
| ----------- | ------------------------------------ |
| 接口路径    | `/project/file/allotFileCategory`    |
| 请求方法    | `POST`                               |
| 前端封装    | `SystemController.allotFileCategory` |
| Swagger Tag | projectManagementApi                 |
| 作用说明    | 分配文件分类                         |

**请求参数（Body）：**

| 字段              | 类型             | 说明     |
| ----------------- | ---------------- | -------- |
| `id`              | `integer`        | 角色ID   |
| `fileCategoryIds` | `array<integer>` | 选中的   |
| `halfIds`         | `array<integer>` | 半选中的 |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.6 获取菜单树

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

### 8.7 获取角色菜单权限树（全树构造）

| 项          | 内容                               |
| ----------- | ---------------------------------- |
| 接口路径    | `/menu/getRoleMenuTree`            |
| 请求方法    | `POST`                             |
| 前端封装    | `SystemController.getRoleMenuTree` |
| Swagger Tag | menuManagementApi                  |
| 作用说明    | 获取角色菜单权限树（全树构造）     |

**请求参数（Body）：**

| 字段       | 类型             | 说明 |
| ---------- | ---------------- | ---- |
| `id`       | `integer`        |      |
| `roleName` | `string`         |      |
| `status`   | `integer`        |      |
| `remark`   | `string`         |      |
| `ids`      | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.8 获取文件分类全树(按角色)

| 项          | 内容                                       |
| ----------- | ------------------------------------------ |
| 接口路径    | `/project/file/getRoleFileCategoryTree`    |
| 请求方法    | `POST`                                     |
| 前端封装    | `SystemController.getRoleFileCategoryTree` |
| Swagger Tag | projectManagementApi                       |
| 作用说明    | 获取文件分类全树(按角色)                   |

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
