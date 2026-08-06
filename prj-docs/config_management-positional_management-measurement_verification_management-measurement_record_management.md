# 计量记录管理（measurement_record_management）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                                                                                  |
| ------------------ | --------------------------------------------------------------------------------------------------------------------- |
| 模块名称（中文）   | 计量记录管理                                                                                                          |
| 模块名称（英文）   | Measurement Record Management                                                                                         |
| 所属 Group（中文） | 计量检定管理                                                                                                          |
| 所属 Group（英文） | Measurement Verification                                                                                              |
| Group ID           | `measurement_verification_management`                                                                                 |
| 菜单位置           | 配置管理平台 → 阵地管理 → 计量检定管理 → 计量记录管理                                                                 |
| 路由路径           | `/config_management/positional_management/measurement_verification_management/measurement_record_management`          |
| 页面目录           | `src/pages/config_management/positional_management/measurement_verification_management/measurement_record_management` |

## 1. 模块定位与项目作用

计量记录管理是综合信息平台中「计量检定管理」业务域下的功能模块，对应页面目录 `src/pages/config_management/positional_management/measurement_verification_management/measurement_record_management`。

在项目中的主要作用：

- 作为「配置管理平台 → 阵地管理 → 计量检定管理 → 计量记录管理」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
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

| 字段名               | 中文含义 | 作用说明                        |
| -------------------- | -------- | ------------------------------- |
| meteringCategory     | 计量型号 | 模块表单/列表字段，详见页面配置 |
| meteringOrganization | 计量人员 | 模块表单/列表字段，详见页面配置 |
| meteringObject       | 计量对象 | 模块表单/列表字段，详见页面配置 |
| meteringCode         | 计量编号 | 模块表单/列表字段，详见页面配置 |
| meteringModel        | 计量型号 | 模块表单/列表字段，详见页面配置 |
| meteringTime         | 计量时间 | 模块表单/列表字段，详见页面配置 |
| meteringValidTime    | 有效时间 | 模块表单/列表字段，详见页面配置 |
| meteringPerson       | 计量人员 | 模块表单/列表字段，详见页面配置 |
| meteringResult       | 计量结果 | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

- 新建/新增
- 编辑
- 删除
- 详情回填
- 导出
- 导入

---

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                                      | 关系说明                                         |
| --------------------------------------------- | ------------------------------------------------ |
| 计量对象管理（measurement_object_management） | 同级功能模块，可共同构成「计量检定管理」业务能力 |

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

本模块（`measurement_record_management`）位于 `src/pages/config_management/positional_management/measurement_verification_management/measurement_record_management`，归属「计量检定管理」。它负责「计量记录管理」相关业务的页面交互与数据读写。维护本模块时，请同步关注接口契约、字段语义及与兄弟模块的数据一致性。

---

## 8. 接口清单

以下接口由本模块页面代码直接或通过 `@/services` Controller 调用，参数与响应 Schema 来自 `swaggerApi.json`（若可匹配）。

### 8.1 获取MisMeteringRecord列表

| 项          | 内容                                            |
| ----------- | ----------------------------------------------- |
| 接口路径    | `/misMeteringRecord/getMisMeteringRecordList`   |
| 请求方法    | `POST`                                          |
| 前端封装    | `PositionalManagement.getMisMeteringRecordList` |
| Swagger Tag | facilityMeteringRecordApi                       |
| 作用说明    | 获取MisMeteringRecord列表                       |

**请求参数（Body）：**

| 字段             | 类型      | 说明 |
| ---------------- | --------- | ---- |
| `page`           | `integer` |      |
| `size`           | `integer` |      |
| `meteringObject` | `string`  |      |
| `meteringCode`   | `string`  |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.2 添加MisMeteringRecord

| 项          | 内容                                        |
| ----------- | ------------------------------------------- |
| 接口路径    | `/misMeteringRecord/addMisMeteringRecord`   |
| 请求方法    | `POST`                                      |
| 前端封装    | `PositionalManagement.addMisMeteringRecord` |
| Swagger Tag | facilityMeteringRecordApi                   |
| 作用说明    | 添加MisMeteringRecord                       |

**请求参数（Body）：**

| 字段                   | 类型     | 说明 |
| ---------------------- | -------- | ---- |
| `meteringObject`       | `string` |      |
| `meteringCode`         | `string` |      |
| `meteringCategory`     | `string` |      |
| `meteringModel`        | `string` |      |
| `meteringTime`         | `string` |      |
| `meteringValidTime`    | `string` |      |
| `meteringResult`       | `string` |      |
| `meteringOrganization` | `string` |      |
| `meteringPerson`       | `string` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.3 获取MisMeteringRecord

| 项          | 内容                                        |
| ----------- | ------------------------------------------- |
| 接口路径    | `/misMeteringRecord/getMisMeteringRecord`   |
| 请求方法    | `POST`                                      |
| 前端封装    | `PositionalManagement.getMisMeteringRecord` |
| Swagger Tag | facilityMeteringRecordApi                   |
| 作用说明    | 获取MisMeteringRecord                       |

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

### 8.4 修改MisMeteringRecord

| 项          | 内容                                         |
| ----------- | -------------------------------------------- |
| 接口路径    | `/misMeteringRecord/editMisMeteringRecord`   |
| 请求方法    | `POST`                                       |
| 前端封装    | `PositionalManagement.editMisMeteringRecord` |
| Swagger Tag | facilityMeteringRecordApi                    |
| 作用说明    | 修改MisMeteringRecord                        |

**请求参数（Body）：**

| 字段                   | 类型      | 说明 |
| ---------------------- | --------- | ---- |
| `id`                   | `integer` |      |
| `meteringObject`       | `string`  |      |
| `meteringCode`         | `string`  |      |
| `meteringCategory`     | `string`  |      |
| `meteringModel`        | `string`  |      |
| `meteringTime`         | `string`  |      |
| `meteringValidTime`    | `string`  |      |
| `meteringResult`       | `string`  |      |
| `meteringOrganization` | `string`  |      |
| `meteringPerson`       | `string`  |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.5 批量删除MisMeteringRecords

| 项          | 内容                                         |
| ----------- | -------------------------------------------- |
| 接口路径    | `/misMeteringRecord/delMisMeteringRecords`   |
| 请求方法    | `POST`                                       |
| 前端封装    | `PositionalManagement.delMisMeteringRecords` |
| Swagger Tag | facilityMeteringRecordApi                    |
| 作用说明    | 批量删除MisMeteringRecords                   |

**请求参数（Body）：**

| 字段  | 类型             | 说明 |
| ----- | ---------------- | ---- |
| `ids` | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.6 导出MisMeteringRecord列表

| 项          | 内容                                               |
| ----------- | -------------------------------------------------- |
| 接口路径    | `/misMeteringRecord/exportMisMeteringRecordList`   |
| 请求方法    | `GET`                                              |
| 前端封装    | `PositionalManagement.exportMisMeteringRecordList` |
| Swagger Tag | facilityMeteringRecordApi                          |
| 作用说明    | 导出MisMeteringRecord列表                          |

**Query/Path 参数：**

| 参数名           | 位置  | 必填 | 类型     | 说明 |
| ---------------- | ----- | ---- | -------- | ---- |
| `page`           | query | 是   | `string` |      |
| `size`           | query | 是   | `string` |      |
| `fieldList[0]`   | query | 否   | `string` |      |
| `meteringObject` | query | 否   | `string` |      |
| `meteringCode`   | query | 否   | `string` |      |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

---

### 8.7 导入MisMeteringRecord数据

| 项          | 内容                                               |
| ----------- | -------------------------------------------------- |
| 接口路径    | `/misMeteringRecord/importMisMeteringRecordList`   |
| 请求方法    | `POST`                                             |
| 前端封装    | `PositionalManagement.importMisMeteringRecordList` |
| Swagger Tag | facilityMeteringRecordApi                          |
| 作用说明    | 导入MisMeteringRecord数据                          |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---
