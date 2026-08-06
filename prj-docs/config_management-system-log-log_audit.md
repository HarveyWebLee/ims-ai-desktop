# 日志审计（log_audit）知识库

> 上级模块索引：[log.md](./log.md) · 总索引：[README.md](./README.md) · 页面总表：[TOTAL-MODULE.md](./TOTAL-MODULE.md)

## 0. 路由与归属信息

| 项                 | 内容                                               |
| ------------------ | -------------------------------------------------- |
| 模块名称（中文）   | 日志审计                                           |
| 模块名称（英文）   | Log Audit                                          |
| 所属 Group（中文） | 日志管理                                           |
| 所属 Group（英文） | Log Management                                     |
| Group ID           | `log`                                              |
| 菜单位置           | 配置管理平台 → 系统管理 → 日志管理 → 日志审计      |
| 路由路径           | `/config_management/system/log_audit`              |
| 页面目录           | `src/pages/config_management/system/log/log_audit` |

## 1. 模块定位与项目作用

日志审计是综合信息平台中「日志管理」业务域下的功能模块，对应页面目录 `src/pages/config_management/system/log/log_audit`。

在项目中的主要作用：

- 作为「配置管理平台 → 系统管理 → 日志管理 → 日志审计」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
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

| 字段名        | 中文含义   | 作用说明                        |
| ------------- | ---------- | ------------------------------- |
| operatorName  | 审计意见   | 模块表单/列表字段，详见页面配置 |
| time          | 时间范围   | 模块表单/列表字段，详见页面配置 |
| auditSerialNo | 审计流水号 | 模块表单/列表字段，详见页面配置 |
| logModule     | 日志模块   | 模块表单/列表字段，详见页面配置 |
| auditStatus   | 审计状态   | 模块表单/列表字段，详见页面配置 |
| auditContent  | 审计意见   | 模块表单/列表字段，详见页面配置 |
| batchAudit    | batchAudit | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

- 删除
- 导出
- 导入

---

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                                | 关系说明                                     |
| --------------------------------------- | -------------------------------------------- |
| 业务应用log（business_application_log） | 同级功能模块，可共同构成「日志管理」业务能力 |
| 设备操作（equipment_operation）         | 同级功能模块，可共同构成「日志管理」业务能力 |
| log策略配置（log_policy_config）        | 同级功能模块，可共同构成「日志管理」业务能力 |
| 网络安全log（network_security_log）     | 同级功能模块，可共同构成「日志管理」业务能力 |
| 系统门禁（system_access）               | 同级功能模块，可共同构成「日志管理」业务能力 |
| 系统操作（system_operation）            | 同级功能模块，可共同构成「日志管理」业务能力 |
| 系统运行log（system_runtime_log）       | 同级功能模块，可共同构成「日志管理」业务能力 |
| 用户行为log（user_behavior_log）        | 同级功能模块，可共同构成「日志管理」业务能力 |

### 5.2 上游依赖 / 下游消费

- **上游**：根据本页接口与字段引用，上游主要为：用户及参数管理（`user`）。另可能依赖登录会话与菜单授权（用户及参数管理）。
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

本模块（`log_audit`）位于 `src/pages/config_management/system/log/log_audit`，归属「日志管理」。它负责「日志审计」相关业务的页面交互与数据读写。维护本模块时，请同步关注接口契约、字段语义及与兄弟模块的数据一致性。

---

## 8. 接口清单

以下接口由本模块页面代码直接或通过 `@/services` Controller 调用，参数与响应 Schema 来自平台 OpenAPI（若可匹配）。

### 8.1 auditLogBatch

| 项       | 内容                               |
| -------- | ---------------------------------- |
| 接口路径 | `/sysMonitor/runLog/auditLogBatch` |
| 请求方法 | `POST`                             |
| 前端封装 | `LogsController.auditLogBatch`     |
| baseURL  | `/api/appv2`                       |
| 作用说明 | 见模块业务逻辑                     |

_未在平台 OpenAPI 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---

### 8.2 更新日志审计

| 项          | 内容                                          |
| ----------- | --------------------------------------------- |
| 接口路径    | `/api/app/sysMonitor/logAudit/updateLogAudit` |
| 请求方法    | `POST`                                        |
| 前端封装    | `LogsController.updateLogAudit`               |
| baseURL     | `/api/appv2`                                  |
| Swagger Tag | appGatewayApi                                 |
| 作用说明    | 更新日志审计                                  |

**Query/Path 参数：**

| 参数名     | 位置  | 必填 | 类型     | 说明 |
| ---------- | ----- | ---- | -------- | ---- |
| `id`       | query | 否   | `string` |      |
| `username` | query | 否   | `string` |      |
| `realname` | query | 否   | `string` |      |
| `roleName` | query | 否   | `string` |      |

**请求参数（Body）：**

| 字段            | 类型     | 说明                                     |
| --------------- | -------- | ---------------------------------------- |
| `id`            | `string` | 分表主键，更新时必填                     |
| `auditSerialNo` | `string` | 审计流水号，新增时可选（未填则自动生成） |
| `recordType`    | `string` |                                          |
| `logModule`     | `string` |                                          |
| `operatorId`    | `string` |                                          |
| `operatorName`  | `string` |                                          |
| `auditStatus`   | `string` |                                          |
| `auditContent`  | `string` |                                          |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.3 日志审计分页查询

| 项          | 内容                                           |
| ----------- | ---------------------------------------------- |
| 接口路径    | `/api/app/sysMonitor/logAudit/getLogAuditPage` |
| 请求方法    | `POST`                                         |
| 前端封装    | `LogsController.getLogAuditPage`               |
| baseURL     | `/api/appv2`                                   |
| Swagger Tag | appGatewayApi                                  |
| 作用说明    | 日志审计分页查询                               |

**请求参数（Body）：**

| 字段            | 类型      | 说明 |
| --------------- | --------- | ---- |
| `startTs`       | `integer` |      |
| `endTs`         | `integer` |      |
| `page`          | `integer` |      |
| `size`          | `integer` |      |
| `auditSerialNo` | `string`  |      |
| `recordType`    | `string`  |      |
| `logModule`     | `string`  |      |
| `operatorId`    | `string`  |      |
| `auditStatus`   | `string`  |      |

**响应体：**

| 字段                           | 类型            | 说明       |
| ------------------------------ | --------------- | ---------- |
| `code`                         | `integer`       |            |
| `message`                      | `string`        |            |
| `data`                         | `object`        |            |
| `data.total`                   | `integer`       |            |
| `data.page`                    | `integer`       |            |
| `data.size`                    | `integer`       |            |
| `data.records`                 | `array<object>` |            |
| `data.records[].id`            | `string`        |            |
| `data.records[].auditSerialNo` | `string`        | 审计流水号 |
| `data.records[].recordType`    | `string`        | 记录类型   |
| `data.records[].logModule`     | `string`        | 日志模块   |
| `data.records[].operatorId`    | `string`        | 操作人 ID  |
| `data.records[].operatorName`  | `string`        | 操作人姓名 |
| `data.records[].auditStatus`   | `string`        | 审计状态   |
| `data.records[].auditContent`  | `string`        | 审计内容   |
| `data.records[].ts`            | `integer`       |            |
| `data.records[].mt`            | `integer`       |            |

---

### 8.4 删除日志审计

| 项          | 内容                                          |
| ----------- | --------------------------------------------- |
| 接口路径    | `/api/app/sysMonitor/logAudit/deleteLogAudit` |
| 请求方法    | `DELETE`                                      |
| 前端封装    | `LogsController.deleteLogAudit`               |
| baseURL     | `/api/appv2`                                  |
| Swagger Tag | appGatewayApi                                 |
| 作用说明    | 删除日志审计                                  |

**Query/Path 参数：**

| 参数名     | 位置  | 必填 | 类型     | 说明 |
| ---------- | ----- | ---- | -------- | ---- |
| `id`       | query | 否   | `string` |      |
| `username` | query | 否   | `string` |      |
| `realname` | query | 否   | `string` |      |
| `roleName` | query | 否   | `string` |      |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.5 日志策略分页查询

| 项          | 内容                                                 |
| ----------- | ---------------------------------------------------- |
| 接口路径    | `/api/app/sysMonitor/logStrategy/getLogStrategyPage` |
| 请求方法    | `POST`                                               |
| 前端封装    | `LogsController.getLogStrategyPage`                  |
| baseURL     | `/api/appv2`                                         |
| Swagger Tag | appGatewayApi                                        |
| 作用说明    | 日志策略分页查询                                     |

**请求参数（Body）：**

| 字段           | 类型      | 说明 |
| -------------- | --------- | ---- |
| `startTs`      | `integer` |      |
| `endTs`        | `integer` |      |
| `page`         | `integer` |      |
| `size`         | `integer` |      |
| `strategyId`   | `string`  |      |
| `logModule`    | `string`  |      |
| `saveTimeUnit` | `string`  |      |

**响应体：**

| 字段                                | 类型            | 说明                                      |
| ----------------------------------- | --------------- | ----------------------------------------- |
| `code`                              | `integer`       |                                           |
| `message`                           | `string`        |                                           |
| `data`                              | `object`        |                                           |
| `data.total`                        | `integer`       |                                           |
| `data.page`                         | `integer`       |                                           |
| `data.size`                         | `integer`       |                                           |
| `data.records`                      | `array<object>` |                                           |
| `data.records[].id`                 | `string`        |                                           |
| `data.records[].strategyId`         | `string`        | 策略 ID                                   |
| `data.records[].logModule`          | `string`        | 日志模块                                  |
| `data.records[].recordPeriodValue`  | `integer`       | 记录周期数值                              |
| `data.records[].recordPeriodUnit`   | `string`        | 记录周期单位：SEC-秒，MIN-分钟，HOUR-小时 |
| `data.records[].saveTimeValue`      | `integer`       | 日志保存时间数值                          |
| `data.records[].saveTimeUnit`       | `string`        | 日志保存时间单位：DAY-天，YEAR-年         |
| `data.records[].recordFrequencySec` | `integer`       | 日志记录频率（秒/次）                     |
| `data.records[].ts`                 | `integer`       |                                           |
| `data.records[].mt`                 | `integer`       |                                           |

---

### 8.6 新增日志策略

| 项          | 内容                                             |
| ----------- | ------------------------------------------------ |
| 接口路径    | `/api/app/sysMonitor/logStrategy/addLogStrategy` |
| 请求方法    | `POST`                                           |
| 前端封装    | `LogsController.addLogStrategy`                  |
| baseURL     | `/api/appv2`                                     |
| Swagger Tag | appGatewayApi                                    |
| 作用说明    | 新增日志策略                                     |

**Query/Path 参数：**

| 参数名     | 位置  | 必填 | 类型     | 说明 |
| ---------- | ----- | ---- | -------- | ---- |
| `id`       | query | 否   | `string` |      |
| `username` | query | 否   | `string` |      |
| `realname` | query | 否   | `string` |      |
| `roleName` | query | 否   | `string` |      |

**请求参数（Body）：**

| 字段                 | 类型      | 说明                                      |
| -------------------- | --------- | ----------------------------------------- |
| `id`                 | `string`  | 分表主键，更新时必填                      |
| `strategyId`         | `string`  | 策略 ID，新增时可选（未填则自动生成）     |
| `logModule`          | `string`  |                                           |
| `recordPeriodValue`  | `integer` | 记录周期数值                              |
| `recordPeriodUnit`   | `string`  | 记录周期单位：SEC-秒，MIN-分钟，HOUR-小时 |
| `saveTimeValue`      | `integer` | 日志保存时间数值                          |
| `saveTimeUnit`       | `string`  | 日志保存时间单位：DAY-天，YEAR-年         |
| `recordFrequencySec` | `integer` | 日志记录频率（秒/次）                     |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `string`  |      |

---

### 8.7 更新日志策略

| 项          | 内容                                                |
| ----------- | --------------------------------------------------- |
| 接口路径    | `/api/app/sysMonitor/logStrategy/updateLogStrategy` |
| 请求方法    | `POST`                                              |
| 前端封装    | `LogsController.updateLogStrategy`                  |
| baseURL     | `/api/appv2`                                        |
| Swagger Tag | appGatewayApi                                       |
| 作用说明    | 更新日志策略                                        |

**Query/Path 参数：**

| 参数名     | 位置  | 必填 | 类型     | 说明 |
| ---------- | ----- | ---- | -------- | ---- |
| `id`       | query | 否   | `string` |      |
| `username` | query | 否   | `string` |      |
| `realname` | query | 否   | `string` |      |
| `roleName` | query | 否   | `string` |      |

**请求参数（Body）：**

| 字段                 | 类型      | 说明                                      |
| -------------------- | --------- | ----------------------------------------- |
| `id`                 | `string`  | 分表主键，更新时必填                      |
| `strategyId`         | `string`  | 策略 ID，新增时可选（未填则自动生成）     |
| `logModule`          | `string`  |                                           |
| `recordPeriodValue`  | `integer` | 记录周期数值                              |
| `recordPeriodUnit`   | `string`  | 记录周期单位：SEC-秒，MIN-分钟，HOUR-小时 |
| `saveTimeValue`      | `integer` | 日志保存时间数值                          |
| `saveTimeUnit`       | `string`  | 日志保存时间单位：DAY-天，YEAR-年         |
| `recordFrequencySec` | `integer` | 日志记录频率（秒/次）                     |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.8 删除日志策略

| 项          | 内容                                                |
| ----------- | --------------------------------------------------- |
| 接口路径    | `/api/app/sysMonitor/logStrategy/deleteLogStrategy` |
| 请求方法    | `DELETE`                                            |
| 前端封装    | `LogsController.deleteLogStrategy`                  |
| baseURL     | `/api/appv2`                                        |
| Swagger Tag | appGatewayApi                                       |
| 作用说明    | 删除日志策略                                        |

**Query/Path 参数：**

| 参数名     | 位置  | 必填 | 类型     | 说明 |
| ---------- | ----- | ---- | -------- | ---- |
| `id`       | query | 否   | `string` |      |
| `username` | query | 否   | `string` |      |
| `realname` | query | 否   | `string` |      |
| `roleName` | query | 否   | `string` |      |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---
