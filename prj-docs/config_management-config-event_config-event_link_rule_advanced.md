# 事件联动规则（高级）（event_link_rule_advanced）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                                       |
| ------------------ | -------------------------------------------------------------------------- |
| 模块名称（中文）   | 事件联动规则（高级）                                                       |
| 模块名称（英文）   | Event Link Rule Advanced                                                   |
| 所属 Group（中文） | 事件配置                                                                   |
| 所属 Group（英文） | Event Config                                                               |
| Group ID           | `event_config`                                                             |
| 菜单位置           | 配置管理平台 → 配置管理 → 事件配置 → 事件联动规则（高级）                  |
| 路由路径           | `/config_management/config/event_config/event_link_rule_advanced`          |
| 页面目录           | `src/pages/config_management/config/event_config/event_link_rule_advanced` |

## 1. 模块定位与项目作用

事件联动规则（高级）是综合信息平台中「事件配置」业务域下的功能模块，对应页面目录 `src/pages/config_management/config/event_config/event_link_rule_advanced`。

在项目中的主要作用：

- 作为「配置管理平台 → 配置管理 → 事件配置 → 事件联动规则（高级）」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
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

| 字段名               | 中文含义           | 作用说明                        |
| -------------------- | ------------------ | ------------------------------- |
| id                   | 名称               | 模块表单/列表字段，详见页面配置 |
| linkageFlowConfigRow | 事件流配置         | 模块表单/列表字段，详见页面配置 |
| eventName            | 名称               | 模块表单/列表字段，详见页面配置 |
| eventStatus          | 事件状态           | 模块表单/列表字段，详见页面配置 |
| execType             | 执行类型           | 模块表单/列表字段，详见页面配置 |
| dn                   | 设备编号           | 模块表单/列表字段，详见页面配置 |
| vn                   | 变量名称           | 模块表单/列表字段，详见页面配置 |
| validTime            | 事件探测周期(s)    | 模块表单/列表字段，详见页面配置 |
| timeout              | 超时时间(s)        | 模块表单/列表字段，详见页面配置 |
| scheduleTime         | 变量推送周期(s)    | 模块表单/列表字段，详见页面配置 |
| eventParam           | 事件源设置         | 模块表单/列表字段，详见页面配置 |
| eventExpress         | 事件规则表达式     | 模块表单/列表字段，详见页面配置 |
| timeoutPlaceholder   | timeoutPlaceholder | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

- 新建/新增
- 编辑
- 删除
- 详情回填
- 导出
- 导入
- 复制
- 启用/停用

---

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                               | 关系说明                                     |
| -------------------------------------- | -------------------------------------------- |
| 周期事件配置（cycle_event_config）     | 同级功能模块，可共同构成「事件配置」业务能力 |
| 事件执行记录（event_execution_record） | 同级功能模块，可共同构成「事件配置」业务能力 |
| 事件流程配置（event_flow_config）      | 同级功能模块，可共同构成「事件配置」业务能力 |
| 事件联动规则（event_link_rule）        | 同级功能模块，可共同构成「事件配置」业务能力 |
| 事件规则记录（event_rule_record）      | 同级功能模块，可共同构成「事件配置」业务能力 |

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

本模块（`event_link_rule_advanced`）位于 `src/pages/config_management/config/event_config/event_link_rule_advanced`，归属「事件配置」。它负责「事件联动规则（高级）」相关业务的页面交互与数据读写。维护本模块时，请同步关注接口契约、字段语义及与兄弟模块的数据一致性。

---

## 8. 接口清单

以下接口由本模块页面代码直接或通过 `@/services` Controller 调用，参数与响应 Schema 来自 `swaggerApi.json`（若可匹配）。

### 8.1 getEventFlowConfigById

| 项       | 内容                                           |
| -------- | ---------------------------------------------- |
| 接口路径 | `未知`                                         |
| 请求方法 | `未知`                                         |
| 前端封装 | `EventStreamController.getEventFlowConfigById` |
| 作用说明 | 见模块业务逻辑                                 |

_未在 `swaggerApi.json` 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---

### 8.2 人工核验事件分页查询

| 项          | 内容                                            |
| ----------- | ----------------------------------------------- |
| 接口路径    | `/api/appv2/event/manualCheckEvent/queryPage`   |
| 请求方法    | `POST`                                          |
| 前端封装    | `SystemController.queryEventConfigPageAdvanced` |
| baseURL     | `/api/appv2`                                    |
| Swagger Tag | appGatewayApi                                   |
| 作用说明    | 人工核验事件分页查询                            |

**请求参数（Body）：**

| 字段         | 类型      | 说明                                              |
| ------------ | --------- | ------------------------------------------------- |
| `page`       | `integer` | 页码（从1开始）                                   |
| `size`       | `integer` | 每页大小                                          |
| `mid`        | `string`  | 查询条件：mid                                     |
| `event`      | `string`  | 查询条件：触发事件（模糊匹配）                    |
| `ruleId`     | `integer` | 查询条件：规则ID                                  |
| `execStatus` | `string`  | 查询条件：执行状态（INIT/RUNNING/SUCCESS/FAILED） |

**响应体：**

| 字段                        | 类型            | 说明                                     |
| --------------------------- | --------------- | ---------------------------------------- |
| `code`                      | `integer`       |                                          |
| `message`                   | `string`        |                                          |
| `data`                      | `object`        |                                          |
| `data.current`              | `integer`       |                                          |
| `data.pages`                | `integer`       |                                          |
| `data.size`                 | `integer`       |                                          |
| `data.total`                | `integer`       |                                          |
| `data.records`              | `array<object>` |                                          |
| `data.records[].id`         | `integer`       | 主键                                     |
| `data.records[].event`      | `string`        | 触发事件列表，英文逗号分隔               |
| `data.records[].ruleId`     | `integer`       | 时间联动规则ID                           |
| `data.records[].mid`        | `string`        | 幂等处理唯一编号                         |
| `data.records[].params`     | `string`        | 指令下发相关参数                         |
| `data.records[].execStatus` | `string`        | 执行状态：INIT、RUNNING、SUCCESS、FAILED |
| `data.records[].createTime` | `integer`       | 创建时间（毫秒时间戳）                   |
| `data.records[].modifyTime` | `integer`       | 修改时间（毫秒时间戳）                   |

---

### 8.3 新增事件流快照

| 项          | 内容                                       |
| ----------- | ------------------------------------------ |
| 接口路径    | `/api/appv2/event/flow-version/save`       |
| 请求方法    | `POST`                                     |
| 前端封装    | `SystemController.saveEventConfigAdvanced` |
| baseURL     | `/api/appv2`                               |
| Swagger Tag | appGatewayApi                              |
| 作用说明    | 新增事件流快照                             |

**请求参数（Body）：**

| 字段          | 类型      | 说明            |
| ------------- | --------- | --------------- |
| `flowVersion` | `string`  | 流程版本        |
| `flowId`      | `integer` | 流程ID          |
| `flowCode`    | `string`  | 流程编码        |
| `flowName`    | `string`  | 流程名称        |
| `flowType`    | `string`  | 流程类型        |
| `sourceCode`  | `string`  | 来源编码        |
| `status`      | `string`  | 状态，默认 INIT |
| `remark`      | `string`  | 备注            |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.4 更新流程配置（id 放在请求体中）

| 项          | 内容                                         |
| ----------- | -------------------------------------------- |
| 接口路径    | `/api/appv2/event/flow/update`               |
| 请求方法    | `POST`                                       |
| 前端封装    | `SystemController.updateEventConfigAdvanced` |
| baseURL     | `/api/appv2`                                 |
| Swagger Tag | appGatewayApi                                |
| 作用说明    | 更新流程配置（id 放在请求体中）              |

**请求参数（Body）：**

| 字段             | 类型      | 说明                                                                                                             |
| ---------------- | --------- | ---------------------------------------------------------------------------------------------------------------- |
| `id`             | `integer` | 主键ID                                                                                                           |
| `flowCode`       | `string`  | 流程编码（唯一）                                                                                                 |
| `flowName`       | `string`  | 流程名称                                                                                                         |
| `flowType`       | `string`  | 流程类型（NORMAL-普通流程, APPROVAL-审批流程, AUTOMATION-自动化流程）；枚举: MANUAL_AND_AUTO, AUTOMATION, MANUAL |
| `flowJson`       | `string`  | 流程JSON配置，须为符合{@link com.boomy.component.app.sharding.request.flowjson.FlowGraph} 的 JSON。              |
| `originFlowJson` | `string`  | 原始流程JSON配置（未编辑前的备份）                                                                               |
| `sourceCode`     | `string`  | 来源编码                                                                                                         |
| `status`         | `string`  | 状态；枚举: ENABLED, DISABLED, INIT                                                                              |
| `currVersionId`  | `integer` | 当前关联的流程版本ID（t_event_flow_version.id）                                                                  |
| `remark`         | `string`  | 备注                                                                                                             |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.5 deleteEventConfigAdvanced

| 项       | 内容                                         |
| -------- | -------------------------------------------- |
| 接口路径 | `未知`                                       |
| 请求方法 | `未知`                                       |
| 前端封装 | `SystemController.deleteEventConfigAdvanced` |
| 作用说明 | 见模块业务逻辑                               |

_未在 `swaggerApi.json` 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---

### 8.6 getEventConfigAdvanced

| 项       | 内容                                      |
| -------- | ----------------------------------------- |
| 接口路径 | `未知`                                    |
| 请求方法 | `未知`                                    |
| 前端封装 | `SystemController.getEventConfigAdvanced` |
| 作用说明 | 见模块业务逻辑                            |

_未在 `swaggerApi.json` 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---

### 8.7 exportEventConfigAdvanced

| 项       | 内容                                         |
| -------- | -------------------------------------------- |
| 接口路径 | `/eventConfig/export`                        |
| 请求方法 | `GET`                                        |
| 前端封装 | `SystemController.exportEventConfigAdvanced` |
| baseURL  | `/api/appv2`                                 |
| 作用说明 | 见模块业务逻辑                               |

_未在 `swaggerApi.json` 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---

### 8.8 导入值班管理

| 项          | 内容                                         |
| ----------- | -------------------------------------------- |
| 接口路径    | `/duty/import`                               |
| 请求方法    | `POST`                                       |
| 前端封装    | `SystemController.importEventConfigAdvanced` |
| baseURL     | `/api/appv2`                                 |
| Swagger Tag | dutyManagementApi                            |
| 作用说明    | 导入值班管理                                 |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `string`  |      |

---

### 8.9 批量修改状态

| 项          | 内容                                           |
| ----------- | ---------------------------------------------- |
| 接口路径    | `/eventRule/updateEventRuleStatus`             |
| 请求方法    | `POST`                                         |
| 前端封装    | `SystemController.updateEventConfigRuleStatus` |
| baseURL     | `/api/appv2`                                   |
| Swagger Tag | eventRuleApi                                   |
| 作用说明    | 批量修改状态                                   |

**请求参数（Body）：**

| 字段          | 类型             | 说明 |
| ------------- | ---------------- | ---- |
| `eventStatus` | `integer`        |      |
| `ids`         | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.10 checkAviatorScript

| 项       | 内容                                  |
| -------- | ------------------------------------- |
| 接口路径 | `/aviator/checkAviatorScript`         |
| 请求方法 | `POST`                                |
| 前端封装 | `SystemController.checkAviatorScript` |
| 作用说明 | 见模块业务逻辑                        |

_未在 `swaggerApi.json` 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---

### 8.11 getEventFlowConfigPage

| 项       | 内容                                           |
| -------- | ---------------------------------------------- |
| 接口路径 | `未知`                                         |
| 请求方法 | `未知`                                         |
| 前端封装 | `EventStreamController.getEventFlowConfigPage` |
| 作用说明 | 见模块业务逻辑                                 |

_未在 `swaggerApi.json` 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---
