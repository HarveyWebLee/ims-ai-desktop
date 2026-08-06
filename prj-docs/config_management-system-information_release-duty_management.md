# 值班管理（duty_management）知识库

> 上级模块索引：[information_release.md](./information_release.md) · 总索引：[README.md](./README.md) · 页面总表：[TOTAL-MODULE.md](./TOTAL-MODULE.md)

## 0. 路由与归属信息

| 项                 | 内容                                                                     |
| ------------------ | ------------------------------------------------------------------------ |
| 模块名称（中文）   | 值班管理                                                                 |
| 模块名称（英文）   | Duty Management                                                          |
| 所属 Group（中文） | 信息发布                                                                 |
| 所属 Group（英文） | Information Release                                                      |
| Group ID           | `information_release`                                                    |
| 菜单位置           | 配置管理平台 → 系统管理 → 信息发布 → 值班管理                            |
| 路由路径           | `/config_management/system/duty_management`                              |
| 页面目录           | `src/pages/config_management/system/information_release/duty_management` |

## 1. 模块定位与项目作用

执勤管理是综合信息平台中「信息发布」业务域下的功能模块，对应页面目录 `src/pages/config_management/system/information_release/duty_management`。

在项目中的主要作用：

- 作为「配置管理平台 → 系统管理 → 信息发布 → 执勤管理」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
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

| 字段名          | 中文含义    | 作用说明                        |
| --------------- | ----------- | ------------------------------- |
| airDutyPerson   | 信息化      | 模块表单/列表字段，详见页面配置 |
| infoDutyPerson  | 给排水      | 模块表单/列表字段，详见页面配置 |
| waterDutyPerson | 发供电      | 模块表单/列表字段，详见页面配置 |
| time            | 预留值班员1 | 模块表单/列表字段，详见页面配置 |
| dic1            | 预留值班员2 | 模块表单/列表字段，详见页面配置 |
| dic2            | 预留值班员3 | 模块表单/列表字段，详见页面配置 |
| dic3            | 预留值班员4 | 模块表单/列表字段，详见页面配置 |
| dic4            | 预留值班员5 | 模块表单/列表字段，详见页面配置 |
| dic5            | 备注        | 模块表单/列表字段，详见页面配置 |
| startTime       | 开始时间    | 模块表单/列表字段，详见页面配置 |
| endTime         | 结束时间    | 模块表单/列表字段，详见页面配置 |
| dutyLeader      | 值班首长    | 模块表单/列表字段，详见页面配置 |
| dutyPerson      | 值班员      | 模块表单/列表字段，详见页面配置 |
| dutyPerson1     | 值班员1     | 模块表单/列表字段，详见页面配置 |
| powerDutyPerson | 发供电      | 模块表单/列表字段，详见页面配置 |
| remark          | 备注        | 模块表单/列表字段，详见页面配置 |

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

| 关联模块                                  | 关系说明                                     |
| ----------------------------------------- | -------------------------------------------- |
| information发布（information_fabu）       | 同级功能模块，可共同构成「信息发布」业务能力 |
| information管理（information_management） | 同级功能模块，可共同构成「信息发布」业务能力 |

### 5.2 上游依赖 / 下游消费

- **上游**：根据本页接口与字段引用，上游主要为：日常值班（`daily_duty`）、用户及参数管理（`user`）。另可能依赖登录会话与菜单授权（用户及参数管理）。
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

本模块（`duty_management`）位于 `src/pages/config_management/system/information_release/duty_management`，归属「信息发布」。它负责「执勤管理」相关业务的页面交互与数据读写。维护本模块时，请同步关注接口契约、字段语义及与兄弟模块的数据一致性。

---

## 8. 接口清单

以下接口由本模块页面代码直接或通过 `@/services` Controller 调用，参数与响应 Schema 来自平台 OpenAPI（若可匹配）。

### 8.1 获取值班信息管理

| 项          | 内容                                 |
| ----------- | ------------------------------------ |
| 接口路径    | `/duty/getDutyManageList`            |
| 请求方法    | `POST`                               |
| 前端封装    | `SystemController.getDutyManageList` |
| Swagger Tag | dutyManagementApi                    |
| 作用说明    | 获取值班信息管理                     |

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
| `startTime`      | `string`        |      |
| `endTime`        | `string`        |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.2 导出值班管理

| 项          | 内容                                |
| ----------- | ----------------------------------- |
| 接口路径    | `/duty/exportDutyManage`            |
| 请求方法    | `GET`                               |
| 前端封装    | `SystemController.exportDutyManage` |
| Swagger Tag | dutyManagementApi                   |
| 作用说明    | 导出值班管理                        |

**Query/Path 参数：**

| 参数名            | 位置  | 必填 | 类型     | 说明 |
| ----------------- | ----- | ---- | -------- | ---- |
| `page`            | query | 是   | `string` |      |
| `size`            | query | 是   | `string` |      |
| `search`          | query | 否   | `string` |      |
| `fieldList[0]`    | query | 否   | `string` |      |
| `sorter[0].order` | query | 否   | `string` |      |
| `sorter[0].field` | query | 否   | `string` |      |
| `startTime`       | query | 否   | `string` |      |
| `endTime`         | query | 否   | `string` |      |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

---

### 8.3 添加值班管理

| 项          | 内容                             |
| ----------- | -------------------------------- |
| 接口路径    | `/duty/addDutyManage`            |
| 请求方法    | `POST`                           |
| 前端封装    | `SystemController.addDutyManage` |
| Swagger Tag | dutyManagementApi                |
| 作用说明    | 添加值班管理                     |

**请求参数（Body）：**

| 字段              | 类型             | 说明 |
| ----------------- | ---------------- | ---- |
| `id`              | `integer`        |      |
| `startTime`       | `string`         |      |
| `endTime`         | `string`         |      |
| `dutyPerson`      | `string`         |      |
| `dutyPerson1`     | `string`         |      |
| `airDutyPerson`   | `string`         |      |
| `infoDutyPerson`  | `string`         |      |
| `waterDutyPerson` | `string`         |      |
| `powerDutyPerson` | `string`         |      |
| `remark`          | `string`         |      |
| `dutyLeader`      | `string`         |      |
| `ids`             | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.4 获取值班管理详情

| 项          | 内容                                 |
| ----------- | ------------------------------------ |
| 接口路径    | `/duty/getDutyManageById`            |
| 请求方法    | `POST`                               |
| 前端封装    | `SystemController.getDutyManageById` |
| Swagger Tag | dutyManagementApi                    |
| 作用说明    | 获取值班管理详情                     |

**请求参数（Body）：**

| 字段              | 类型             | 说明 |
| ----------------- | ---------------- | ---- |
| `id`              | `integer`        |      |
| `startTime`       | `string`         |      |
| `endTime`         | `string`         |      |
| `dutyPerson`      | `string`         |      |
| `dutyPerson1`     | `string`         |      |
| `airDutyPerson`   | `string`         |      |
| `infoDutyPerson`  | `string`         |      |
| `waterDutyPerson` | `string`         |      |
| `powerDutyPerson` | `string`         |      |
| `remark`          | `string`         |      |
| `dutyLeader`      | `string`         |      |
| `ids`             | `array<integer>` |      |

**响应体：**

| 字段                   | 类型      | 说明 |
| ---------------------- | --------- | ---- |
| `code`                 | `integer` |      |
| `message`              | `string`  |      |
| `data`                 | `object`  |      |
| `data.id`              | `integer` |      |
| `data.startTime`       | `string`  |      |
| `data.endTime`         | `string`  |      |
| `data.dutyLeader`      | `string`  |      |
| `data.dutyPerson`      | `string`  |      |
| `data.dutyPerson1`     | `string`  |      |
| `data.airDutyPerson`   | `string`  |      |
| `data.infoDutyPerson`  | `string`  |      |
| `data.waterDutyPerson` | `string`  |      |
| `data.powerDutyPerson` | `string`  |      |
| `data.remark`          | `string`  |      |
| `data.createdTime`     | `string`  |      |
| `data.updatedTime`     | `string`  |      |

---

### 8.5 更新值班管理

| 项          | 内容                                |
| ----------- | ----------------------------------- |
| 接口路径    | `/duty/updateDutyManage`            |
| 请求方法    | `POST`                              |
| 前端封装    | `SystemController.updateDutyManage` |
| Swagger Tag | dutyManagementApi                   |
| 作用说明    | 更新值班管理                        |

**请求参数（Body）：**

| 字段              | 类型             | 说明 |
| ----------------- | ---------------- | ---- |
| `id`              | `integer`        |      |
| `startTime`       | `string`         |      |
| `endTime`         | `string`         |      |
| `dutyPerson`      | `string`         |      |
| `dutyPerson1`     | `string`         |      |
| `airDutyPerson`   | `string`         |      |
| `infoDutyPerson`  | `string`         |      |
| `waterDutyPerson` | `string`         |      |
| `powerDutyPerson` | `string`         |      |
| `remark`          | `string`         |      |
| `dutyLeader`      | `string`         |      |
| `ids`             | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.6 删除值班管理

| 项          | 内容                                |
| ----------- | ----------------------------------- |
| 接口路径    | `/duty/deleteDutyManage`            |
| 请求方法    | `POST`                              |
| 前端封装    | `SystemController.deleteDutyManage` |
| Swagger Tag | dutyManagementApi                   |
| 作用说明    | 删除值班管理                        |

**请求参数（Body）：**

| 字段              | 类型             | 说明 |
| ----------------- | ---------------- | ---- |
| `id`              | `integer`        |      |
| `startTime`       | `string`         |      |
| `endTime`         | `string`         |      |
| `dutyPerson`      | `string`         |      |
| `dutyPerson1`     | `string`         |      |
| `airDutyPerson`   | `string`         |      |
| `infoDutyPerson`  | `string`         |      |
| `waterDutyPerson` | `string`         |      |
| `powerDutyPerson` | `string`         |      |
| `remark`          | `string`         |      |
| `dutyLeader`      | `string`         |      |
| `ids`             | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.7 导入值班管理

| 项          | 内容                                |
| ----------- | ----------------------------------- |
| 接口路径    | `/duty/import`                      |
| 请求方法    | `POST`                              |
| 前端封装    | `SystemController.importDutyManage` |
| Swagger Tag | dutyManagementApi                   |
| 作用说明    | 导入值班管理                        |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `string`  |      |

---
