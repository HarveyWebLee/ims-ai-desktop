# 用户管理（user_manage）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                  |
| ------------------ | ----------------------------------------------------- |
| 模块名称（中文）   | 用户管理                                              |
| 模块名称（英文）   | User Manage                                           |
| 所属 Group（中文） | 用户权限                                              |
| 所属 Group（英文） | User & Auth                                           |
| Group ID           | `user`                                                |
| 菜单位置           | 配置管理平台 → 系统管理 → 用户权限 → 用户管理         |
| 路由路径           | `/config_management/system/user/user_manage`          |
| 页面目录           | `src/pages/config_management/system/user/user_manage` |

## 1. 模块定位与项目作用

用户管理是综合信息平台中「用户权限」业务域下的功能模块，对应页面目录 `src/pages/config_management/system/user/user_manage`。

在项目中的主要作用：

- 作为「配置管理平台 → 系统管理 → 用户权限 → 用户管理」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
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

| 字段名       | 中文含义 | 作用说明                        |
| ------------ | -------- | ------------------------------- |
| username     | 用户名   | 模块表单/列表字段，详见页面配置 |
| password     | 用户密码 | 模块表单/列表字段，详见页面配置 |
| sort         | 排序     | 模块表单/列表字段，详见页面配置 |
| realname     | 姓名     | 模块表单/列表字段，详见页面配置 |
| duty         | 职务     | 模块表单/列表字段，详见页面配置 |
| organizeId   | 所属单位 | 模块表单/列表字段，详见页面配置 |
| workStatus   | 在位情况 | 模块表单/列表字段，详见页面配置 |
| adminStatus  | 用户状态 | 模块表单/列表字段，详见页面配置 |
| sex          | 性别     | 模块表单/列表字段，详见页面配置 |
| adminLevel   | 用户等级 | 模块表单/列表字段，详见页面配置 |
| adminGroupId | 用户分组 | 模块表单/列表字段，详见页面配置 |
| roleArray    | 角色     | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

- 新建/新增
- 编辑
- 删除
- 导出
- 导入
- 左侧树筛选

---

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                  | 关系说明                                     |
| ------------------------- | -------------------------------------------- |
| 文件分类（file_category） | 同级功能模块，可共同构成「用户权限」业务能力 |
| 菜单管理（menu_manage）   | 同级功能模块，可共同构成「用户权限」业务能力 |
| 模块管理（module_manage） | 同级功能模块，可共同构成「用户权限」业务能力 |
| 组织机构（organization）  | 同级功能模块，可共同构成「用户权限」业务能力 |
| 角色授权（role_auth）     | 同级功能模块，可共同构成「用户权限」业务能力 |
| 角色管理（role_manage）   | 同级功能模块，可共同构成「用户权限」业务能力 |
| 用户组（user_group）      | 同级功能模块，可共同构成「用户权限」业务能力 |

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

本模块（`user_manage`）位于 `src/pages/config_management/system/user/user_manage`，归属「用户权限」。它负责「用户管理」相关业务的页面交互与数据读写。维护本模块时，请同步关注接口契约、字段语义及与兄弟模块的数据一致性。

---

## 8. 接口清单

以下接口由本模块页面代码直接或通过 `@/services` Controller 调用，参数与响应 Schema 来自 `swaggerApi.json`（若可匹配）。

### 8.1 重置管理员密码

| 项          | 内容                                  |
| ----------- | ------------------------------------- |
| 接口路径    | `/admin/resetAdminPassword`           |
| 请求方法    | `POST`                                |
| 前端封装    | `SystemController.resetAdminPassword` |
| Swagger Tag | adminManagementApi                    |
| 作用说明    | 重置管理员密码                        |

**请求参数（Body）：**

| 字段       | 类型      | 说明 |
| ---------- | --------- | ---- |
| `id`       | `integer` |      |
| `password` | `string`  |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.2 获取管理员列表

| 项          | 内容                            |
| ----------- | ------------------------------- |
| 接口路径    | `/admin/getAdminList`           |
| 请求方法    | `POST`                          |
| 前端封装    | `SystemController.getAdminList` |
| Swagger Tag | adminManagementApi              |
| 作用说明    | 获取管理员列表                  |

**请求参数（Body）：**

| 字段           | 类型            | 说明 |
| -------------- | --------------- | ---- |
| `page`         | `integer`       |      |
| `size`         | `integer`       |      |
| `search`       | `string`        |      |
| `fieldList`    | `array<string>` |      |
| `username`     | `string`        |      |
| `realname`     | `string`        |      |
| `duty`         | `string`        |      |
| `adminGroupId` | `integer`       |      |
| `organizeId`   | `integer`       |      |
| `sex`          | `integer`       |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.3 添加管理员

| 项          | 内容                        |
| ----------- | --------------------------- |
| 接口路径    | `/admin/addAdmin`           |
| 请求方法    | `POST`                      |
| 前端封装    | `SystemController.addAdmin` |
| Swagger Tag | adminManagementApi          |
| 作用说明    | 添加管理员                  |

**请求参数（Body）：**

| 字段           | 类型             | 说明 |
| -------------- | ---------------- | ---- |
| `id`           | `integer`        |      |
| `username`     | `string`         |      |
| `password`     | `string`         |      |
| `realname`     | `string`         |      |
| `sort`         | `integer`        |      |
| `duty`         | `string`         |      |
| `organizeId`   | `integer`        |      |
| `adminStatus`  | `integer`        |      |
| `workStatus`   | `integer`        |      |
| `sex`          | `integer`        |      |
| `adminLevel`   | `integer`        |      |
| `adminGroupId` | `integer`        |      |
| `roleIds`      | `array<integer>` |      |
| `adminIds`     | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.4 修改管理员

| 项          | 内容                         |
| ----------- | ---------------------------- |
| 接口路径    | `/admin/editAdmin`           |
| 请求方法    | `POST`                       |
| 前端封装    | `SystemController.editAdmin` |
| Swagger Tag | adminManagementApi           |
| 作用说明    | 修改管理员                   |

**请求参数（Body）：**

| 字段           | 类型             | 说明 |
| -------------- | ---------------- | ---- |
| `id`           | `integer`        |      |
| `username`     | `string`         |      |
| `password`     | `string`         |      |
| `realname`     | `string`         |      |
| `sort`         | `integer`        |      |
| `duty`         | `string`         |      |
| `organizeId`   | `integer`        |      |
| `adminStatus`  | `integer`        |      |
| `workStatus`   | `integer`        |      |
| `sex`          | `integer`        |      |
| `adminLevel`   | `integer`        |      |
| `adminGroupId` | `integer`        |      |
| `roleIds`      | `array<integer>` |      |
| `adminIds`     | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.5 批量删除管理员

| 项          | 内容                         |
| ----------- | ---------------------------- |
| 接口路径    | `/admin/delAdmins`           |
| 请求方法    | `POST`                       |
| 前端封装    | `SystemController.delAdmins` |
| Swagger Tag | adminManagementApi           |
| 作用说明    | 批量删除管理员               |

**请求参数（Body）：**

| 字段           | 类型             | 说明 |
| -------------- | ---------------- | ---- |
| `id`           | `integer`        |      |
| `username`     | `string`         |      |
| `password`     | `string`         |      |
| `realname`     | `string`         |      |
| `sort`         | `integer`        |      |
| `duty`         | `string`         |      |
| `organizeId`   | `integer`        |      |
| `adminStatus`  | `integer`        |      |
| `workStatus`   | `integer`        |      |
| `sex`          | `integer`        |      |
| `adminLevel`   | `integer`        |      |
| `adminGroupId` | `integer`        |      |
| `roleIds`      | `array<integer>` |      |
| `adminIds`     | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.6 获取组织树

| 项          | 内容                               |
| ----------- | ---------------------------------- |
| 接口路径    | `/organize/getOrganizeTree`        |
| 请求方法    | `POST`                             |
| 前端封装    | `SystemController.getOrganizeTree` |
| Swagger Tag | organizationApi                    |
| 作用说明    | 获取组织树                         |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.7 获取全部用户分组

| 项          | 内容                              |
| ----------- | --------------------------------- |
| 接口路径    | `/adminGroup/getAdminGroups`      |
| 请求方法    | `POST`                            |
| 前端封装    | `SystemController.getAdminGroups` |
| Swagger Tag | adminGroupApi                     |
| 作用说明    | 获取全部用户分组                  |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.8 获取角色数组

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
