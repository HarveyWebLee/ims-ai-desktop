# 执勤日志（duty_logs）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                                     |
| ------------------ | ------------------------------------------------------------------------ |
| 模块名称（中文）   | 执勤日志                                                                 |
| 模块名称（英文）   | Duty Logs                                                                |
| 所属 Group（中文） | 日常执勤                                                                 |
| 所属 Group（英文） | Daily Duty                                                               |
| Group ID           | `daily_duty`                                                             |
| 菜单位置           | 配置管理平台 → 阵地管理 → 日常执勤 → 执勤日志                            |
| 路由路径           | `/config_management/positional_management/daily_duty/duty_logs`          |
| 页面目录           | `src/pages/config_management/positional_management/daily_duty/duty_logs` |

## 1. 模块定位与项目作用

执勤日志是综合信息平台中「日常执勤」业务域下的功能模块，对应页面目录 `src/pages/config_management/positional_management/daily_duty/duty_logs`。

在项目中的主要作用：

- 作为「配置管理平台 → 阵地管理 → 日常执勤 → 执勤日志」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
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

| 字段名           | 中文含义 | 作用说明                        |
| ---------------- | -------- | ------------------------------- |
| auditor          | 审核时间 | 模块表单/列表字段，详见页面配置 |
| auditTime        | 审核状态 | 模块表单/列表字段，详见页面配置 |
| dateString       | 值班日期 | 模块表单/列表字段，详见页面配置 |
| dutyPositionId   | 岗位     | 模块表单/列表字段，详见页面配置 |
| timePeriod       | 时间段   | 模块表单/列表字段，详见页面配置 |
| dutyPositionName | 岗位     | 模块表单/列表字段，详见页面配置 |
| personIds        | 值班人员 | 模块表单/列表字段，详见页面配置 |
| personNames      | 值班人员 | 模块表单/列表字段，详见页面配置 |
| auditStatus      | 审核状态 | 模块表单/列表字段，详见页面配置 |
| remark           | 备注     | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

- 新建/新增
- 编辑
- 删除
- 详情回填
- 导出
- 导入
- 复制

---

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                            | 关系说明                                     |
| ----------------------------------- | -------------------------------------------- |
| 执勤交接（duty_handover）           | 同级功能模块，可共同构成「日常执勤」业务能力 |
| 执勤information（duty_information） | 同级功能模块，可共同构成「日常执勤」业务能力 |
| 执勤人员（duty_personnel）          | 同级功能模块，可共同构成「日常执勤」业务能力 |
| 执勤计划（duty_plan）               | 同级功能模块，可共同构成「日常执勤」业务能力 |
| 执勤设置（duty_setting）            | 同级功能模块，可共同构成「日常执勤」业务能力 |
| 进入退出审批（entry_exit_approval） | 同级功能模块，可共同构成「日常执勤」业务能力 |
| 周交接（week_handover）             | 同级功能模块，可共同构成「日常执勤」业务能力 |

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

本模块（`duty_logs`）位于 `src/pages/config_management/positional_management/daily_duty/duty_logs`，归属「日常执勤」。它负责「执勤日志」相关业务的页面交互与数据读写。维护本模块时，请同步关注接口契约、字段语义及与兄弟模块的数据一致性。

---

## 8. 接口清单

以下接口由本模块页面代码直接或通过 `@/services` Controller 调用，参数与响应 Schema 来自 `swaggerApi.json`（若可匹配）。

### 8.1 按类别名称查询变量数据列表

| 项          | 内容                                                  |
| ----------- | ----------------------------------------------------- |
| 接口路径    | `/api/app/sysMonitor/getDevVarDataListByCategoryName` |
| 请求方法    | `POST`                                                |
| 前端封装    | `SystemController.getDevVarDataListByCategoryName`    |
| baseURL     | `/api/appv2`                                          |
| Swagger Tag | appGatewayApi                                         |
| 作用说明    | 按类别名称查询变量数据列表                            |

**Query/Path 参数：**

| 参数名     | 位置  | 必填 | 类型     | 说明 |
| ---------- | ----- | ---- | -------- | ---- |
| `id`       | query | 否   | `string` |      |
| `username` | query | 否   | `string` |      |
| `realname` | query | 否   | `string` |      |
| `roleName` | query | 否   | `string` |      |

**请求参数（Body）：**

| 字段           | 类型      | 说明                                        |
| -------------- | --------- | ------------------------------------------- |
| `startTime`    | `string`  |                                             |
| `endTime`      | `string`  |                                             |
| `categoryName` | `string`  |                                             |
| `varShowName`  | `string`  | 变量展示名称（show_name），为空时默认“油量” |
| `page`         | `integer` |                                             |
| `size`         | `integer` |                                             |

**响应体：**

| 字段                        | 类型            | 说明                 |
| --------------------------- | --------------- | -------------------- |
| `code`                      | `integer`       |                      |
| `message`                   | `string`        |                      |
| `data`                      | `object`        |                      |
| `data.current`              | `integer`       |                      |
| `data.pages`                | `integer`       |                      |
| `data.size`                 | `integer`       |                      |
| `data.total`                | `integer`       |                      |
| `data.records`              | `array<object>` |                      |
| `data.records[].deviceType` | `string`        | 设备类型             |
| `data.records[].deviceName` | `string`        | 设备名称             |
| `data.records[].varName`    | `string`        | 变量名称             |
| `data.records[].varValue`   | `string`        | 变量值               |
| `data.records[].unit`       | `string`        | 单位                 |
| `data.records[].valueTime`  | `string`        | 变量值时间（格式化） |
| `data.records[].location`   | `string`        | 所在位置             |

---

### 8.2 auditDutyLog

| 项       | 内容                            |
| -------- | ------------------------------- |
| 接口路径 | `/dutyLog/auditDutyLog`         |
| 请求方法 | `POST`                          |
| 前端封装 | `SystemController.auditDutyLog` |
| 作用说明 | 见模块业务逻辑                  |

_未在 `swaggerApi.json` 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---

### 8.3 获取值班日志分页列表

| 项          | 内容                              |
| ----------- | --------------------------------- |
| 接口路径    | `/dutyLog/getDutyLogPage`         |
| 请求方法    | `POST`                            |
| 前端封装    | `SystemController.getDutyLogPage` |
| Swagger Tag | dutyLogApi                        |
| 作用说明    | 获取值班日志分页列表              |

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
| `dateString`     | `string`        |      |
| `dutyPositionId` | `integer`       |      |

**响应体：**

| 字段                              | 类型            | 说明                              |
| --------------------------------- | --------------- | --------------------------------- |
| `code`                            | `integer`       |                                   |
| `message`                         | `string`        |                                   |
| `data`                            | `object`        |                                   |
| `data.records`                    | `array<object>` | 查询数据列表                      |
| `data.records[].id`               | `integer`       |                                   |
| `data.records[].dateString`       | `string`        |                                   |
| `data.records[].cycleId`          | `integer`       |                                   |
| `data.records[].dutyPositionId`   | `integer`       |                                   |
| `data.records[].dutyPositionName` | `string`        |                                   |
| `data.records[].timePeriod`       | `string`        |                                   |
| `data.records[].personIds`        | `string`        |                                   |
| `data.records[].personNames`      | `string`        |                                   |
| `data.records[].remark`           | `string`        | 情况说明                          |
| `data.total`                      | `integer`       | 总数                              |
| `data.size`                       | `integer`       | 每页显示条数，默认 10             |
| `data.current`                    | `integer`       | 当前页                            |
| `data.orders`                     | `array<object>` | 排序字段信息                      |
| `data.orders[].column`            | `string`        | 需要进行排序的字段                |
| `data.orders[].asc`               | `boolean`       | 是否正序排列，默认 true           |
| `data.optimizeCountSql`           | `boolean`       | 自动优化 COUNT SQL                |
| `data.searchCount`                | `boolean`       | 是否进行 count 查询               |
| `data.optimizeJoinOfCountSql`     | `boolean`       | {@link #optimizeJoinOfCountSql()} |
| `data.countId`                    | `string`        | countId                           |
| `data.maxLimit`                   | `integer`       | countId                           |

---

### 8.4 添加值班日志

| 项          | 内容                          |
| ----------- | ----------------------------- |
| 接口路径    | `/dutyLog/addDutyLog`         |
| 请求方法    | `POST`                        |
| 前端封装    | `SystemController.addDutyLog` |
| Swagger Tag | dutyLogApi                    |
| 作用说明    | 添加值班日志                  |

**请求参数（Body）：**

| 字段             | 类型             | 说明     |
| ---------------- | ---------------- | -------- |
| `id`             | `integer`        |          |
| `dateString`     | `string`         |          |
| `cycleId`        | `integer`        |          |
| `dutyPositionId` | `integer`        |          |
| `timePeriod`     | `string`         |          |
| `personIds`      | `string`         |          |
| `remark`         | `string`         | 情况说明 |
| `ids`            | `array<integer>` |          |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.5 获取值班日志

| 项          | 内容                          |
| ----------- | ----------------------------- |
| 接口路径    | `/dutyLog/getDutyLog`         |
| 请求方法    | `POST`                        |
| 前端封装    | `SystemController.getDutyLog` |
| Swagger Tag | dutyLogApi                    |
| 作用说明    | 获取值班日志                  |

**请求参数（Body）：**

| 字段             | 类型             | 说明     |
| ---------------- | ---------------- | -------- |
| `id`             | `integer`        |          |
| `dateString`     | `string`         |          |
| `cycleId`        | `integer`        |          |
| `dutyPositionId` | `integer`        |          |
| `timePeriod`     | `string`         |          |
| `personIds`      | `string`         |          |
| `remark`         | `string`         | 情况说明 |
| `ids`            | `array<integer>` |          |

**响应体：**

| 字段                    | 类型      | 说明     |
| ----------------------- | --------- | -------- |
| `code`                  | `integer` |          |
| `message`               | `string`  |          |
| `data`                  | `object`  |          |
| `data.id`               | `integer` |          |
| `data.dateString`       | `string`  |          |
| `data.cycleId`          | `integer` |          |
| `data.dutyPositionId`   | `integer` |          |
| `data.dutyPositionName` | `string`  |          |
| `data.timePeriod`       | `string`  |          |
| `data.personIds`        | `string`  |          |
| `data.personNames`      | `string`  |          |
| `data.remark`           | `string`  | 情况说明 |

---

### 8.6 修改值班日志

| 项          | 内容                             |
| ----------- | -------------------------------- |
| 接口路径    | `/dutyLog/updateDutyLog`         |
| 请求方法    | `POST`                           |
| 前端封装    | `SystemController.updateDutyLog` |
| Swagger Tag | dutyLogApi                       |
| 作用说明    | 修改值班日志                     |

**请求参数（Body）：**

| 字段             | 类型             | 说明     |
| ---------------- | ---------------- | -------- |
| `id`             | `integer`        |          |
| `dateString`     | `string`         |          |
| `cycleId`        | `integer`        |          |
| `dutyPositionId` | `integer`        |          |
| `timePeriod`     | `string`         |          |
| `personIds`      | `string`         |          |
| `remark`         | `string`         | 情况说明 |
| `ids`            | `array<integer>` |          |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.7 删除值班日志

| 项          | 内容                             |
| ----------- | -------------------------------- |
| 接口路径    | `/dutyLog/deleteDutyLog`         |
| 请求方法    | `POST`                           |
| 前端封装    | `SystemController.deleteDutyLog` |
| Swagger Tag | dutyLogApi                       |
| 作用说明    | 删除值班日志                     |

**请求参数（Body）：**

| 字段             | 类型             | 说明     |
| ---------------- | ---------------- | -------- |
| `id`             | `integer`        |          |
| `dateString`     | `string`         |          |
| `cycleId`        | `integer`        |          |
| `dutyPositionId` | `integer`        |          |
| `timePeriod`     | `string`         |          |
| `personIds`      | `string`         |          |
| `remark`         | `string`         | 情况说明 |
| `ids`            | `array<integer>` |          |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.8 获取告警记录列表

| 项          | 内容                            |
| ----------- | ------------------------------- |
| 接口路径    | `/alarm/getAlarmList`           |
| 请求方法    | `POST`                          |
| 前端封装    | `SystemController.getAlarmList` |
| Swagger Tag | alarmManagementApi              |
| 作用说明    | 获取告警记录列表                |

**请求参数（Body）：**

| 字段              | 类型            | 说明             |
| ----------------- | --------------- | ---------------- |
| `page`            | `integer`       |                  |
| `size`            | `integer`       |                  |
| `search`          | `string`        |                  |
| `fieldList`       | `array<string>` |                  |
| `sorter`          | `array<object>` |                  |
| `sorter[].order`  | `string`        |                  |
| `sorter[].field`  | `string`        |                  |
| `subSystemId`     | `integer`       |                  |
| `alarmCategoryId` | `integer`       |                  |
| `alarmRankId`     | `integer`       |                  |
| `status`          | `integer`       |                  |
| `startTime`       | `string`        |                  |
| `endTime`         | `string`        |                  |
| `deviceCombId`    | `integer`       | 新增组合设备查询 |
| `regionId`        | `integer`       | 区域id           |
| `isIncludeSub`    | `integer`       | 是否包含下级     |
| `deviceCodes`     | `array<string>` | 新增设备编码集合 |
| `variableNames`   | `array<string>` | 新增变量名称集合 |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.9 获取岗位配置列表

| 项          | 内容                                   |
| ----------- | -------------------------------------- |
| 接口路径    | `/dutyPosition/getDutyPositionList`    |
| 请求方法    | `POST`                                 |
| 前端封装    | `SystemController.getDutyPositionList` |
| Swagger Tag | dutyPositionApi                        |
| 作用说明    | 获取岗位配置列表                       |

**请求参数（Body）：**

| 字段           | 类型             | 说明 |
| -------------- | ---------------- | ---- |
| `id`           | `integer`        |      |
| `positionName` | `string`         |      |
| `personNum`    | `integer`        |      |
| `remark`       | `string`         |      |
| `ids`          | `array<integer>` |      |

**响应体：**

| 字段                  | 类型            | 说明 |
| --------------------- | --------------- | ---- |
| `code`                | `integer`       |      |
| `message`             | `string`        |      |
| `data`                | `array<object>` |      |
| `data[].id`           | `integer`       |      |
| `data[].positionName` | `string`        |      |
| `data[].personNum`    | `integer`       |      |
| `data[].remark`       | `string`        |      |
| `data[].createdTime`  | `string`        |      |
| `data[].updatedTime`  | `string`        |      |

---

### 8.10 获取阵地人员列表

| 项          | 内容                                     |
| ----------- | ---------------------------------------- |
| 接口路径    | `/positionPerson/getPositionPersonList`  |
| 请求方法    | `POST`                                   |
| 前端封装    | `SystemController.getPositionPersonList` |
| Swagger Tag | positionPersonnelApi                     |
| 作用说明    | 获取阵地人员列表                         |

**请求参数（Body）：**

| 字段           | 类型             | 说明 |
| -------------- | ---------------- | ---- |
| `id`           | `integer`        |      |
| `personName`   | `string`         |      |
| `militaryName` | `string`         |      |
| `profession`   | `string`         |      |
| `major`        | `string`         |      |
| `skillLevel`   | `string`         |      |
| `ids`          | `array<integer>` |      |

**响应体：**

| 字段                  | 类型            | 说明 |
| --------------------- | --------------- | ---- |
| `code`                | `integer`       |      |
| `message`             | `string`        |      |
| `data`                | `array<object>` |      |
| `data[].id`           | `integer`       |      |
| `data[].personName`   | `string`        |      |
| `data[].militaryName` | `string`        |      |
| `data[].profession`   | `string`        |      |
| `data[].major`        | `string`        |      |
| `data[].skillLevel`   | `string`        |      |
| `data[].createdTime`  | `string`        |      |
| `data[].updatedTime`  | `string`        |      |

---

### 8.11 获取MisFaultLibrary列表

| 项          | 内容                                          |
| ----------- | --------------------------------------------- |
| 接口路径    | `/misFaultLibrary/getMisFaultLibraryList`     |
| 请求方法    | `POST`                                        |
| 前端封装    | `PositionalManagement.getMisFaultLibraryList` |
| Swagger Tag | facilityFaultLibraryApi                       |
| 作用说明    | 获取MisFaultLibrary列表                       |

**请求参数（Body）：**

| 字段              | 类型      | 说明 |
| ----------------- | --------- | ---- |
| `page`            | `integer` |      |
| `size`            | `integer` |      |
| `faultDeviceName` | `string`  |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---
