# 岗哨交接（guard_post_handover）知识库

> 上级模块索引：[door_access_system.md](./door_access_system.md) · 总索引：[README.md](./README.md) · 页面总表：[TOTAL-MODULE.md](./TOTAL-MODULE.md)

## 0. 路由与归属信息

| 项                 | 内容                                                                        |
| ------------------ | --------------------------------------------------------------------------- |
| 模块名称（中文）   | 岗哨交接                                                                    |
| 模块名称（英文）   | Guard Post Handover                                                         |
| 所属 Group（中文） | 门禁系统                                                                    |
| 所属 Group（英文） | Door Access System                                                          |
| Group ID           | `door_access_system`                                                        |
| 菜单位置           | 配置管理平台 → 系统管理 → 门禁系统 → 岗哨交接                               |
| 路由路径           | `/config_management/system/guard_post_handover`                             |
| 页面目录           | `src/pages/config_management/system/door_access_system/guard_post_handover` |

## 1. 模块定位与项目作用

哨位岗位交接是综合信息平台中「门禁系统」业务域下的功能模块，对应页面目录 `src/pages/config_management/system/door_access_system/guard_post_handover`。

在项目中的主要作用：

- 作为「配置管理平台 → 系统管理 → 门禁系统 → 哨位岗位交接」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
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

| 字段名        | 中文含义     | 作用说明                        |
| ------------- | ------------ | ------------------------------- |
| sentryName    | 带班员       | 模块表单/列表字段，详见页面配置 |
| shiftLeader   | 交接岗位时间 | 模块表单/列表字段，详见页面配置 |
| takeSentinel  | 查岗人       | 模块表单/列表字段，详见页面配置 |
| sentryId      | 岗哨信息     | 模块表单/列表字段，详见页面配置 |
| handoverTime  | 交接岗位时间 | 模块表单/列表字段，详见页面配置 |
| handSentinel  | 交岗哨兵     | 模块表单/列表字段，详见页面配置 |
| checkPerson   | 查岗人       | 模块表单/列表字段，详见页面配置 |
| dutySituation | 当班情况     | 模块表单/列表字段，详见页面配置 |
| remark        | 备注         | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

- 新建/新增
- 编辑
- 删除
- 导出
- 导入

---

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                                                         | 关系说明                                     |
| ---------------------------------------------------------------- | -------------------------------------------- |
| Access Information Maintenance（access_information_maintenance） | 同级功能模块，可共同构成「门禁系统」业务能力 |
| 门禁统计（access_statistics）                                    | 同级功能模块，可共同构成「门禁系统」业务能力 |
| door门禁同步（door_access_sync）                                 | 同级功能模块，可共同构成「门禁系统」业务能力 |
| 执勤信息（duty_info）                                            | 同级功能模块，可共同构成「门禁系统」业务能力 |
| 入出仓储（in_out_storage）                                       | 同级功能模块，可共同构成「门禁系统」业务能力 |
| 内部仓储（inner_storage）                                        | 同级功能模块，可共同构成「门禁系统」业务能力 |
| 安全检查（safety_check）                                         | 同级功能模块，可共同构成「门禁系统」业务能力 |

### 5.2 上游依赖 / 下游消费

- **上游**：根据本页接口与字段引用，上游主要为：日常值班（`daily_duty`）、用户及参数管理（`user`）、基础数据（`basedata`）。另可能依赖登录会话与菜单授权（用户及参数管理）。
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

本模块（`guard_post_handover`）位于 `src/pages/config_management/system/door_access_system/guard_post_handover`，归属「门禁系统」。它负责「哨位岗位交接」相关业务的页面交互与数据读写。维护本模块时，请同步关注接口契约、字段语义及与兄弟模块的数据一致性。

---

## 8. 接口清单

以下接口由本模块页面代码直接或通过 `@/services` Controller 调用，参数与响应 Schema 来自平台 OpenAPI（若可匹配）。

### 8.1 获取岗哨交接信息列表

| 项          | 内容                                     |
| ----------- | ---------------------------------------- |
| 接口路径    | `/duty/getSentryHandoverList`            |
| 请求方法    | `POST`                                   |
| 前端封装    | `SystemController.getSentryHandoverList` |
| Swagger Tag | dutyManagementApi                        |
| 作用说明    | 获取岗哨交接信息列表                     |

**请求参数（Body）：**

| 字段             | 类型            | 说明 |
| ---------------- | --------------- | ---- |
| `page`           | `integer`       |      |
| `size`           | `integer`       |      |
| `search`         | `string`        |      |
| `fieldList`      | `array<string>` |      |
| `sorter`         | `array<object>` |      |
| `sorter[].order` | `string`        |      |
| `sorter[].field` | `string`        |      |
| `sentryId`       | `integer`       |      |
| `startTime`      | `string`        |      |
| `endTime`        | `string`        |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.2 添加岗哨交接信息

| 项          | 内容                                 |
| ----------- | ------------------------------------ |
| 接口路径    | `/duty/addSentryHandover`            |
| 请求方法    | `POST`                               |
| 前端封装    | `SystemController.addSentryHandover` |
| Swagger Tag | dutyManagementApi                    |
| 作用说明    | 添加岗哨交接信息                     |

**请求参数（Body）：**

| 字段            | 类型             | 说明 |
| --------------- | ---------------- | ---- |
| `id`            | `integer`        |      |
| `sentryId`      | `integer`        |      |
| `shiftLeader`   | `string`         |      |
| `handoverTime`  | `string`         |      |
| `handSentinel`  | `string`         |      |
| `takeSentinel`  | `string`         |      |
| `checkPerson`   | `string`         |      |
| `dutySituation` | `string`         |      |
| `remark`        | `string`         |      |
| `ids`           | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.3 更新岗哨交接信息

| 项          | 内容                                    |
| ----------- | --------------------------------------- |
| 接口路径    | `/duty/updateSentryHandover`            |
| 请求方法    | `POST`                                  |
| 前端封装    | `SystemController.updateSentryHandover` |
| Swagger Tag | dutyManagementApi                       |
| 作用说明    | 更新岗哨交接信息                        |

**请求参数（Body）：**

| 字段            | 类型             | 说明 |
| --------------- | ---------------- | ---- |
| `id`            | `integer`        |      |
| `sentryId`      | `integer`        |      |
| `shiftLeader`   | `string`         |      |
| `handoverTime`  | `string`         |      |
| `handSentinel`  | `string`         |      |
| `takeSentinel`  | `string`         |      |
| `checkPerson`   | `string`         |      |
| `dutySituation` | `string`         |      |
| `remark`        | `string`         |      |
| `ids`           | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.4 删除岗哨交接信息

| 项          | 内容                                    |
| ----------- | --------------------------------------- |
| 接口路径    | `/duty/deleteSentryHandover`            |
| 请求方法    | `POST`                                  |
| 前端封装    | `SystemController.deleteSentryHandover` |
| Swagger Tag | dutyManagementApi                       |
| 作用说明    | 删除岗哨交接信息                        |

**请求参数（Body）：**

| 字段            | 类型             | 说明 |
| --------------- | ---------------- | ---- |
| `id`            | `integer`        |      |
| `sentryId`      | `integer`        |      |
| `shiftLeader`   | `string`         |      |
| `handoverTime`  | `string`         |      |
| `handSentinel`  | `string`         |      |
| `takeSentinel`  | `string`         |      |
| `checkPerson`   | `string`         |      |
| `dutySituation` | `string`         |      |
| `remark`        | `string`         |      |
| `ids`           | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.5 导出岗哨交接信息

| 项          | 内容                                    |
| ----------- | --------------------------------------- |
| 接口路径    | `/duty/exportSentryHandover`            |
| 请求方法    | `GET`                                   |
| 前端封装    | `SystemController.exportSentryHandover` |
| Swagger Tag | dutyManagementApi                       |
| 作用说明    | 导出岗哨交接信息                        |

**Query/Path 参数：**

| 参数名            | 位置  | 必填 | 类型     | 说明 |
| ----------------- | ----- | ---- | -------- | ---- |
| `page`            | query | 是   | `string` |      |
| `size`            | query | 是   | `string` |      |
| `search`          | query | 否   | `string` |      |
| `fieldList[0]`    | query | 否   | `string` |      |
| `sorter[0].order` | query | 否   | `string` |      |
| `sorter[0].field` | query | 否   | `string` |      |
| `sentryId`        | query | 否   | `string` |      |
| `startTime`       | query | 否   | `string` |      |
| `endTime`         | query | 否   | `string` |      |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

---

### 8.6 获取岗哨信息列表

| 项          | 内容                                 |
| ----------- | ------------------------------------ |
| 接口路径    | `/sentry/getSentryInfoList`          |
| 请求方法    | `POST`                               |
| 前端封装    | `SystemController.getSentryInfoList` |
| Swagger Tag | sentryApi                            |
| 作用说明    | 获取岗哨信息列表                     |

**请求参数（Body）：**

| 字段        | 类型            | 说明 |
| ----------- | --------------- | ---- |
| `page`      | `integer`       |      |
| `size`      | `integer`       |      |
| `search`    | `string`        |      |
| `fieldList` | `array<string>` |      |
| `sentryNo`  | `string`        |      |
| `location`  | `string`        |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---
