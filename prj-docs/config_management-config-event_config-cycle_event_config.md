# 周期事件配置（cycle_event_config）知识库

> 上级模块索引：[event_config.md](./event_config.md) · 总索引：[README.md](./README.md) · 页面总表：[TOTAL-MODULE.md](./TOTAL-MODULE.md)

## 0. 路由与归属信息

| 项                 | 内容                                                                 |
| ------------------ | -------------------------------------------------------------------- |
| 模块名称（中文）   | 周期事件配置                                                         |
| 模块名称（英文）   | Cycle Event Config                                                   |
| 所属 Group（中文） | 事件配置                                                             |
| 所属 Group（英文） | Event Config                                                         |
| Group ID           | `event_config`                                                       |
| 菜单位置           | 配置管理平台 → 配置管理 → 事件配置 → 周期事件配置                    |
| 路由路径           | `/config_management/config/cycle_event_config`                       |
| 页面目录           | `src/pages/config_management/config/event_config/cycle_event_config` |

## 1. 模块定位与项目作用

周期事件配置是综合信息平台中「事件配置」业务域下的功能模块，对应页面目录 `src/pages/config_management/config/event_config/cycle_event_config`。

在项目中的主要作用：

- 作为「配置管理平台 → 配置管理 → 事件配置 → 周期事件配置」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
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

| 字段名              | 中文含义 | 作用说明                        |
| ------------------- | -------- | ------------------------------- |
| id                  | 名称     | 模块表单/列表字段，详见页面配置 |
| scheduleName        | 名称     | 模块表单/列表字段，详见页面配置 |
| configType          | 配置方式 | 模块表单/列表字段，详见页面配置 |
| scheduleStatus      | 事件状态 | 模块表单/列表字段，详见页面配置 |
| cronRule            | 周期设置 | 模块表单/列表字段，详见页面配置 |
| scheduleConfig      | 联动配置 | 模块表单/列表字段，详见页面配置 |
| scheduleConfigTable | 联动配置 | 模块表单/列表字段，详见页面配置 |

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

| 关联模块                                         | 关系说明                                     |
| ------------------------------------------------ | -------------------------------------------- |
| 事件执行记录（event_execution_record）           | 同级功能模块，可共同构成「事件配置」业务能力 |
| 事件流程配置（event_flow_config）                | 同级功能模块，可共同构成「事件配置」业务能力 |
| 事件联动规则（event_link_rule）                  | 同级功能模块，可共同构成「事件配置」业务能力 |
| 事件联动规则（高级）（event_link_rule_advanced） | 同级功能模块，可共同构成「事件配置」业务能力 |
| 事件规则记录（event_rule_record）                | 同级功能模块，可共同构成「事件配置」业务能力 |

### 5.2 上游依赖 / 下游消费

- **上游**：根据本页接口与字段引用，上游主要为：用户及参数管理（`user`）、基础数据（`basedata`）。另可能依赖登录会话与菜单授权（用户及参数管理）。
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

本模块（`cycle_event_config`）位于 `src/pages/config_management/config/event_config/cycle_event_config`，归属「事件配置」。它负责「周期事件配置」相关业务的页面交互与数据读写。维护本模块时，请同步关注接口契约、字段语义及与兄弟模块的数据一致性。

---

## 8. 接口清单

以下接口由本模块页面代码直接或通过 `@/services` Controller 调用，参数与响应 Schema 来自平台 OpenAPI（若可匹配）。

### 8.1 获取计划任务列表

| 项          | 内容                                   |
| ----------- | -------------------------------------- |
| 接口路径    | `/scheduleRule/getScheduleRuleList`    |
| 请求方法    | `POST`                                 |
| 前端封装    | `SystemController.getScheduleRuleList` |
| Swagger Tag | scheduleRuleApi                        |
| 作用说明    | 获取计划任务列表                       |

**请求参数（Body）：**

| 字段             | 类型            | 说明 |
| ---------------- | --------------- | ---- |
| `scheduleName`   | `string`        |      |
| `scheduleStatus` | `integer`       |      |
| `page`           | `integer`       |      |
| `size`           | `integer`       |      |
| `search`         | `string`        |      |
| `fieldList`      | `array<string>` |      |
| `sorter`         | `array<object>` |      |
| `sorter[].order` | `string`        |      |
| `sorter[].field` | `string`        |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.2 添加计划任务

| 项          | 内容                               |
| ----------- | ---------------------------------- |
| 接口路径    | `/scheduleRule/addScheduleRule`    |
| 请求方法    | `POST`                             |
| 前端封装    | `SystemController.addScheduleRule` |
| Swagger Tag | scheduleRuleApi                    |
| 作用说明    | 添加计划任务                       |

**请求参数（Body）：**

| 字段             | 类型             | 说明 |
| ---------------- | ---------------- | ---- |
| `id`             | `integer`        |      |
| `scheduleName`   | `string`         |      |
| `scheduleConfig` | `string`         |      |
| `scheduleStatus` | `integer`        |      |
| `cronRule`       | `string`         |      |
| `ids`            | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.3 修改计划任务

| 项          | 内容                                |
| ----------- | ----------------------------------- |
| 接口路径    | `/scheduleRule/editScheduleRule`    |
| 请求方法    | `POST`                              |
| 前端封装    | `SystemController.editScheduleRule` |
| Swagger Tag | scheduleRuleApi                     |
| 作用说明    | 修改计划任务                        |

**请求参数（Body）：**

| 字段             | 类型             | 说明 |
| ---------------- | ---------------- | ---- |
| `id`             | `integer`        |      |
| `scheduleName`   | `string`         |      |
| `scheduleConfig` | `string`         |      |
| `scheduleStatus` | `integer`        |      |
| `cronRule`       | `string`         |      |
| `ids`            | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.4 批量删除计划任务

| 项          | 内容                               |
| ----------- | ---------------------------------- |
| 接口路径    | `/scheduleRule/delScheduleRules`   |
| 请求方法    | `POST`                             |
| 前端封装    | `SystemController.delScheduleRule` |
| Swagger Tag | scheduleRuleApi                    |
| 作用说明    | 批量删除计划任务                   |

**请求参数（Body）：**

| 字段             | 类型             | 说明 |
| ---------------- | ---------------- | ---- |
| `id`             | `integer`        |      |
| `scheduleName`   | `string`         |      |
| `scheduleConfig` | `string`         |      |
| `scheduleStatus` | `integer`        |      |
| `cronRule`       | `string`         |      |
| `ids`            | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.5 获取计划任务

| 项          | 内容                               |
| ----------- | ---------------------------------- |
| 接口路径    | `/scheduleRule/getScheduleRule`    |
| 请求方法    | `POST`                             |
| 前端封装    | `SystemController.getScheduleRule` |
| Swagger Tag | scheduleRuleApi                    |
| 作用说明    | 获取计划任务                       |

**请求参数（Body）：**

| 字段             | 类型             | 说明 |
| ---------------- | ---------------- | ---- |
| `id`             | `integer`        |      |
| `scheduleName`   | `string`         |      |
| `scheduleConfig` | `string`         |      |
| `scheduleStatus` | `integer`        |      |
| `cronRule`       | `string`         |      |
| `ids`            | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.6 导出计划任务列表

| 项          | 内容                                      |
| ----------- | ----------------------------------------- |
| 接口路径    | `/scheduleRule/exportScheduleRuleList`    |
| 请求方法    | `GET`                                     |
| 前端封装    | `SystemController.exportScheduleRuleList` |
| Swagger Tag | scheduleRuleApi                           |
| 作用说明    | 导出计划任务列表                          |

**Query/Path 参数：**

| 参数名            | 位置  | 必填 | 类型     | 说明 |
| ----------------- | ----- | ---- | -------- | ---- |
| `scheduleName`    | query | 否   | `string` |      |
| `scheduleStatus`  | query | 否   | `string` |      |
| `page`            | query | 是   | `string` |      |
| `size`            | query | 是   | `string` |      |
| `search`          | query | 否   | `string` |      |
| `fieldList[0]`    | query | 否   | `string` |      |
| `sorter[0].order` | query | 否   | `string` |      |
| `sorter[0].field` | query | 否   | `string` |      |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

---

### 8.7 导入计划任务数据

| 项          | 内容                                      |
| ----------- | ----------------------------------------- |
| 接口路径    | `/scheduleRule/importScheduleRuleList`    |
| 请求方法    | `POST`                                    |
| 前端封装    | `SystemController.importScheduleRuleList` |
| Swagger Tag | scheduleRuleApi                           |
| 作用说明    | 导入计划任务数据                          |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.8 导入更新计划任务数据

| 项          | 内容                                            |
| ----------- | ----------------------------------------------- |
| 接口路径    | `/scheduleRule/importUpdateScheduleRuleList`    |
| 请求方法    | `POST`                                          |
| 前端封装    | `SystemController.importUpdateScheduleRuleList` |
| Swagger Tag | scheduleRuleApi                                 |
| 作用说明    | 导入更新计划任务数据                            |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.9 计划任务数据校验

| 项          | 内容                                 |
| ----------- | ------------------------------------ |
| 接口路径    | `/scheduleRule/checkScheduleData`    |
| 请求方法    | `POST`                               |
| 前端封装    | `SystemController.checkScheduleData` |
| Swagger Tag | scheduleRuleApi                      |
| 作用说明    | 计划任务数据校验                     |

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

### 8.10 批量修改计划任务状态

| 项          | 内容                                    |
| ----------- | --------------------------------------- |
| 接口路径    | `/scheduleRule/updateScheduleStatus`    |
| 请求方法    | `POST`                                  |
| 前端封装    | `SystemController.updateScheduleStatus` |
| Swagger Tag | scheduleRuleApi                         |
| 作用说明    | 批量修改计划任务状态                    |

**请求参数（Body）：**

| 字段             | 类型             | 说明 |
| ---------------- | ---------------- | ---- |
| `id`             | `integer`        |      |
| `scheduleName`   | `string`         |      |
| `scheduleConfig` | `string`         |      |
| `scheduleStatus` | `integer`        |      |
| `cronRule`       | `string`         |      |
| `ids`            | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---
