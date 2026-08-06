# 二次变量（second_var）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                            |
| ------------------ | --------------------------------------------------------------- |
| 模块名称（中文）   | 二次变量                                                        |
| 模块名称（英文）   | Second Variable                                                 |
| 所属 Group（中文） | 设备变量                                                        |
| 所属 Group（英文） | Device Variable                                                 |
| Group ID           | `device_variable`                                               |
| 菜单位置           | 配置管理平台 → 配置管理 → 设备变量 → 二次变量                   |
| 路由路径           | `/config_management/config/second_var`                          |
| 页面目录           | `src/pages/config_management/config/device_variable/second_var` |

## 1. 模块定位与项目作用

二次变量是综合信息平台中「设备变量」业务域下的功能模块，对应页面目录 `src/pages/config_management/config/device_variable/second_var`。

在项目中的主要作用：

- 作为「配置管理平台 → 配置管理 → 设备变量 → 二次变量」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
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

| 字段名                | 中文含义                       | 作用说明                        |
| --------------------- | ------------------------------ | ------------------------------- |
| secondRuleParam       | secondVarVariableResultConfig  | 模块表单/列表字段，详见页面配置 |
| secondRuleResult      | secondVarEventRuleExpression   | 模块表单/列表字段，详见页面配置 |
| configType            | secondVarConfigMode            | 模块表单/列表字段，详见页面配置 |
| id                    | primaryKeyId                   | 模块表单/列表字段，详见页面配置 |
| secondRuleName        | name                           | 模块表单/列表字段，详见页面配置 |
| secondRuleType        | secondVarRuleType              | 模块表单/列表字段，详见页面配置 |
| secondRuleStatus      | secondVarRuleStatus            | 模块表单/列表字段，详见页面配置 |
| validTime             | secondVarValidTime             | 模块表单/列表字段，详见页面配置 |
| secondRuleExpress     | secondVarEventRuleExpression   | 模块表单/列表字段，详见页面配置 |
| secondRuleParamTable  | secondVarVariableSourceSetting | 模块表单/列表字段，详见页面配置 |
| secondRuleResultTable | secondVarVariableResultSetting | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

- 新建/新增
- 编辑
- 删除
- 详情回填
- 导出
- 导入
- 批量修改导入
- 复制
- 启用/停用

---

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                           | 关系说明                                     |
| ---------------------------------- | -------------------------------------------- |
| 实时变量数据（real_time_var_data） | 同级功能模块，可共同构成「设备变量」业务能力 |
| 设备变量（var）                    | 同级功能模块，可共同构成「设备变量」业务能力 |
| 变量告警配置（var_alarm_config）   | 同级功能模块，可共同构成「设备变量」业务能力 |

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

本模块（`second_var`）位于 `src/pages/config_management/config/device_variable/second_var`，归属「设备变量」。它负责「二次变量」相关业务的页面交互与数据读写。维护本模块时，请同步关注接口契约、字段语义及与兄弟模块的数据一致性。

---

## 8. 接口清单

以下接口由本模块页面代码直接或通过 `@/services` Controller 调用，参数与响应 Schema 来自 `swaggerApi.json`（若可匹配）。

### 8.1 模拟事件联动

| 项          | 内容                                 |
| ----------- | ------------------------------------ |
| 接口路径    | `/ruleScript/execSecondaryTest`      |
| 请求方法    | `POST`                               |
| 前端封装    | `SystemController.execSecondaryTest` |
| Swagger Tag | ruleScriptApi                        |
| 作用说明    | 模拟事件联动                         |

**请求参数（Body）：**

| 字段          | 类型      | 说明 |
| ------------- | --------- | ---- |
| `id`          | `integer` |      |
| `dataMap`     | `object`  |      |
| `dataMap.key` | `object`  |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.2 批量修改状态

| 项          | 内容                                      |
| ----------- | ----------------------------------------- |
| 接口路径    | `/ruleScript/updateSecondRuleStatus`      |
| 请求方法    | `POST`                                    |
| 前端封装    | `SystemController.updateSecondRuleStatus` |
| Swagger Tag | ruleScriptApi                             |
| 作用说明    | 批量修改状态                              |

**请求参数（Body）：**

| 字段               | 类型             | 说明 |
| ------------------ | ---------------- | ---- |
| `secondRuleStatus` | `integer`        |      |
| `ids`              | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.3 获取二次规则列表

| 项          | 内容                                 |
| ----------- | ------------------------------------ |
| 接口路径    | `/ruleScript/getSecondRuleList`      |
| 请求方法    | `POST`                               |
| 前端封装    | `SystemController.getSecondRuleList` |
| Swagger Tag | ruleScriptApi                        |
| 作用说明    | 获取二次规则列表                     |

**请求参数（Body）：**

| 字段               | 类型      | 说明 |
| ------------------ | --------- | ---- |
| `secondRuleName`   | `string`  |      |
| `secondRuleType`   | `string`  |      |
| `secondRuleStatus` | `integer` |      |
| `page`             | `integer` |      |
| `size`             | `integer` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.4 添加二次规则

| 项          | 内容                             |
| ----------- | -------------------------------- |
| 接口路径    | `/ruleScript/addSecondRule`      |
| 请求方法    | `POST`                           |
| 前端封装    | `SystemController.addSecondRule` |
| Swagger Tag | ruleScriptApi                    |
| 作用说明    | 添加二次规则                     |

**请求参数（Body）：**

| 字段                | 类型      | 说明 |
| ------------------- | --------- | ---- |
| `secondRuleName`    | `string`  |      |
| `secondRuleType`    | `string`  |      |
| `secondRuleParam`   | `string`  |      |
| `secondRuleResult`  | `string`  |      |
| `secondRuleExpress` | `string`  |      |
| `secondRuleStatus`  | `integer` |      |
| `validTime`         | `integer` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.5 修改事件联动规则

| 项          | 内容                              |
| ----------- | --------------------------------- |
| 接口路径    | `/ruleScript/editSecondRule`      |
| 请求方法    | `POST`                            |
| 前端封装    | `SystemController.editSecondRule` |
| Swagger Tag | ruleScriptApi                     |
| 作用说明    | 修改事件联动规则                  |

**请求参数（Body）：**

| 字段                | 类型      | 说明 |
| ------------------- | --------- | ---- |
| `id`                | `integer` |      |
| `secondRuleName`    | `string`  |      |
| `secondRuleType`    | `string`  |      |
| `secondRuleParam`   | `string`  |      |
| `secondRuleResult`  | `string`  |      |
| `secondRuleExpress` | `string`  |      |
| `secondRuleStatus`  | `integer` |      |
| `validTime`         | `integer` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.6 删除事件联动规则

| 项          | 内容                              |
| ----------- | --------------------------------- |
| 接口路径    | `/ruleScript/delSecondRules`      |
| 请求方法    | `POST`                            |
| 前端封装    | `SystemController.delSecondRules` |
| Swagger Tag | ruleScriptApi                     |
| 作用说明    | 删除事件联动规则                  |

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

### 8.7 获取二次规则详情

| 项          | 内容                             |
| ----------- | -------------------------------- |
| 接口路径    | `/ruleScript/getSecondRule`      |
| 请求方法    | `POST`                           |
| 前端封装    | `SystemController.getSecondRule` |
| Swagger Tag | ruleScriptApi                    |
| 作用说明    | 获取二次规则详情                 |

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

### 8.8 导出二次规则列表

| 项          | 内容                                    |
| ----------- | --------------------------------------- |
| 接口路径    | `/ruleScript/exportSecondRuleList`      |
| 请求方法    | `GET`                                   |
| 前端封装    | `SystemController.exportSecondRuleList` |
| Swagger Tag | ruleScriptApi                           |
| 作用说明    | 导出二次规则列表                        |

**Query/Path 参数：**

| 参数名             | 位置  | 必填 | 类型     | 说明 |
| ------------------ | ----- | ---- | -------- | ---- |
| `secondRuleName`   | query | 否   | `string` |      |
| `secondRuleType`   | query | 否   | `string` |      |
| `secondRuleStatus` | query | 否   | `string` |      |
| `page`             | query | 是   | `string` |      |
| `size`             | query | 是   | `string` |      |
| `fieldList[0]`     | query | 否   | `string` |      |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

---

### 8.9 导入二次规则数据

| 项          | 内容                                    |
| ----------- | --------------------------------------- |
| 接口路径    | `/ruleScript/importSecondRuleList`      |
| 请求方法    | `POST`                                  |
| 前端封装    | `SystemController.importSecondRuleList` |
| Swagger Tag | ruleScriptApi                           |
| 作用说明    | 导入二次规则数据                        |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.10 导入二次规则更新数据

| 项          | 内容                                          |
| ----------- | --------------------------------------------- |
| 接口路径    | `/ruleScript/importUpdateSecondRuleList`      |
| 请求方法    | `POST`                                        |
| 前端封装    | `SystemController.importUpdateSecondRuleList` |
| Swagger Tag | ruleScriptApi                                 |
| 作用说明    | 导入二次规则更新数据                          |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.11 checkSecondRuleData

| 项       | 内容                                   |
| -------- | -------------------------------------- |
| 接口路径 | `/ruleScript/checkSecondRuleData`      |
| 请求方法 | `POST`                                 |
| 前端封装 | `SystemController.checkSecondRuleData` |
| 作用说明 | 见模块业务逻辑                         |

_未在 `swaggerApi.json` 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---

### 8.12 clearSecondRuleCache

| 项       | 内容                                    |
| -------- | --------------------------------------- |
| 接口路径 | `/ruleScript/clearSecondRuleCache`      |
| 请求方法 | `POST`                                  |
| 前端封装 | `SystemController.clearSecondRuleCache` |
| 作用说明 | 见模块业务逻辑                          |

_未在 `swaggerApi.json` 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---

### 8.13 checkAviatorScript

| 项       | 内容                                  |
| -------- | ------------------------------------- |
| 接口路径 | `/aviator/checkAviatorScript`         |
| 请求方法 | `POST`                                |
| 前端封装 | `SystemController.checkAviatorScript` |
| 作用说明 | 见模块业务逻辑                        |

_未在 `swaggerApi.json` 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---
