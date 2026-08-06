# 变量报警配置（var_alarm_config）知识库

> 上级模块索引：[device_variable.md](./device_variable.md) · 总索引：[README.md](./README.md) · 页面总表：[TOTAL-MODULE.md](./TOTAL-MODULE.md)

## 0. 路由与归属信息

| 项                 | 内容                                                                  |
| ------------------ | --------------------------------------------------------------------- |
| 模块名称（中文）   | 变量报警配置                                                          |
| 模块名称（英文）   | Variable Alarm Config                                                 |
| 所属 Group（中文） | 设备变量                                                              |
| 所属 Group（英文） | Device Variable                                                       |
| Group ID           | `device_variable`                                                     |
| 菜单位置           | 配置管理平台 → 配置管理 → 设备变量 → 变量报警配置                     |
| 路由路径           | `/config_management/config/var_alarm_config`                          |
| 页面目录           | `src/pages/config_management/config/device_variable/var_alarm_config` |

## 1. 模块定位与项目作用

变量告警配置是综合信息平台中「设备变量」业务域下的功能模块，对应页面目录 `src/pages/config_management/config/device_variable/var_alarm_config`。

在项目中的主要作用：

- 作为「配置管理平台 → 配置管理 → 设备变量 → 变量告警配置」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
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

| 字段名            | 中文含义         | 作用说明                        |
| ----------------- | ---------------- | ------------------------------- |
| alarmSourceName   | 处理预案         | 模块表单/列表字段，详见页面配置 |
| id                | 序号             | 模块表单/列表字段，详见页面配置 |
| varId             | 选择变量         | 模块表单/列表字段，详见页面配置 |
| deviceCode        | 设备编码         | 模块表单/列表字段，详见页面配置 |
| varName           | 变量名称         | 模块表单/列表字段，详见页面配置 |
| alarmName         | 告警事件名称     | 模块表单/列表字段，详见页面配置 |
| isPopup           | 是否显示告警弹窗 | 模块表单/列表字段，详见页面配置 |
| priority          | 告警优先级       | 模块表单/列表字段，详见页面配置 |
| alarmRankId       | 告警级别         | 模块表单/列表字段，详见页面配置 |
| alarmRankName     | 告警级别名称     | 模块表单/列表字段，详见页面配置 |
| alarmCategoryId   | 告警类别         | 模块表单/列表字段，详见页面配置 |
| alarmCategoryName | 告警类别名称     | 模块表单/列表字段，详见页面配置 |
| riskLevel         | 告警风险等级     | 模块表单/列表字段，详见页面配置 |
| alarmSourceId     | 告警源           | 模块表单/列表字段，详见页面配置 |
| handingPlan       | 处理预案         | 模块表单/列表字段，详见页面配置 |
| isDefend          | 是否布防         | 模块表单/列表字段，详见页面配置 |

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
- 左侧树筛选

---

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                           | 关系说明                                     |
| ---------------------------------- | -------------------------------------------- |
| 实时变量数据（real_time_var_data） | 同级功能模块，可共同构成「设备变量」业务能力 |
| 二次变量（second_var）             | 同级功能模块，可共同构成「设备变量」业务能力 |
| 设备变量（var）                    | 同级功能模块，可共同构成「设备变量」业务能力 |

### 5.2 上游依赖 / 下游消费

- **上游**：根据本页接口与字段引用，上游主要为：报警查询统计（`alarm_query_statistics`）、监控设备（`monitor_equipment`）、字典表（`dic_table`）、用户及参数管理（`user`）、基础数据（`basedata`）。另可能依赖登录会话与菜单授权（用户及参数管理）。
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

本模块（`var_alarm_config`）位于 `src/pages/config_management/config/device_variable/var_alarm_config`，归属「设备变量」。它负责「变量告警配置」相关业务的页面交互与数据读写。维护本模块时，请同步关注接口契约、字段语义及与兄弟模块的数据一致性。

---

## 8. 接口清单

以下接口由本模块页面代码直接或通过 `@/services` Controller 调用，参数与响应 Schema 来自平台 OpenAPI（若可匹配）。

### 8.1 分页查询变量告警属性

| 项          | 内容                                        |
| ----------- | ------------------------------------------- |
| 接口路径    | `/alarmVarProperty/getAlarmVarPropertyPage` |
| 请求方法    | `POST`                                      |
| 前端封装    | `SystemController.getAlarmVarPropertyPage`  |
| Swagger Tag | alarmVariablePropertyApi                    |
| 作用说明    | 分页查询变量告警属性                        |

**请求参数（Body）：**

| 字段              | 类型            | 说明 |
| ----------------- | --------------- | ---- |
| `page`            | `integer`       |      |
| `size`            | `integer`       |      |
| `search`          | `string`        |      |
| `fieldList`       | `array<string>` |      |
| `sorter`          | `array<object>` |      |
| `sorter[].order`  | `string`        |      |
| `sorter[].field`  | `string`        |      |
| `varId`           | `integer`       |      |
| `priority`        | `string`        |      |
| `alarmRankId`     | `integer`       |      |
| `alarmCategoryId` | `integer`       |      |
| `alarmName`       | `string`        |      |
| `riskLevel`       | `string`        |      |
| `alarmSourceId`   | `integer`       |      |
| `alarmColor`      | `string`        |      |

**响应体：**

| 字段                                | 类型            | 说明                              |
| ----------------------------------- | --------------- | --------------------------------- |
| `code`                              | `integer`       |                                   |
| `message`                           | `string`        |                                   |
| `data`                              | `object`        |                                   |
| `data.records`                      | `array<object>` | 查询数据列表                      |
| `data.records[].id`                 | `integer`       |                                   |
| `data.records[].deviceCode`         | `string`        |                                   |
| `data.records[].varId`              | `integer`       |                                   |
| `data.records[].varName`            | `string`        |                                   |
| `data.records[].priority`           | `string`        |                                   |
| `data.records[].alarmRankId`        | `integer`       |                                   |
| `data.records[].alarmRankName`      | `string`        |                                   |
| `data.records[].alarmCategoryId`    | `integer`       |                                   |
| `data.records[].alarmCategoryName`  | `string`        |                                   |
| `data.records[].alarmName`          | `string`        |                                   |
| `data.records[].riskLevel`          | `string`        |                                   |
| `data.records[].alarmSourceId`      | `integer`       |                                   |
| `data.records[].alarmSourceName`    | `string`        |                                   |
| `data.records[].alarmColor`         | `string`        |                                   |
| `data.records[].handingPlan`        | `string`        |                                   |
| `data.records[].isDefend`           | `integer`       |                                   |
| `data.records[].alarmStatusVarName` | `string`        |                                   |
| `data.records[].createdTime`        | `string`        |                                   |
| `data.records[].updatedTime`        | `string`        |                                   |
| `data.total`                        | `integer`       | 总数                              |
| `data.size`                         | `integer`       | 每页显示条数，默认 10             |
| `data.current`                      | `integer`       | 当前页                            |
| `data.orders`                       | `array<object>` | 排序字段信息                      |
| `data.orders[].column`              | `string`        | 需要进行排序的字段                |
| `data.orders[].asc`                 | `boolean`       | 是否正序排列，默认 true           |
| `data.optimizeCountSql`             | `boolean`       | 自动优化 COUNT SQL                |
| `data.searchCount`                  | `boolean`       | 是否进行 count 查询               |
| `data.optimizeJoinOfCountSql`       | `boolean`       | {@link #optimizeJoinOfCountSql()} |
| `data.countId`                      | `string`        | countId                           |
| `data.maxLimit`                     | `integer`       | countId                           |

---

### 8.2 新增变量告警属性

| 项          | 内容                                    |
| ----------- | --------------------------------------- |
| 接口路径    | `/alarmVarProperty/addAlarmVarProperty` |
| 请求方法    | `POST`                                  |
| 前端封装    | `SystemController.addAlarmVarProperty`  |
| Swagger Tag | alarmVariablePropertyApi                |
| 作用说明    | 新增变量告警属性                        |

**请求参数（Body）：**

| 字段                 | 类型      | 说明 |
| -------------------- | --------- | ---- |
| `id`                 | `integer` |      |
| `deviceCode`         | `string`  |      |
| `varId`              | `integer` |      |
| `varName`            | `string`  |      |
| `priority`           | `string`  |      |
| `alarmRankId`        | `integer` |      |
| `alarmCategoryId`    | `integer` |      |
| `alarmName`          | `string`  |      |
| `riskLevel`          | `string`  |      |
| `alarmSourceId`      | `integer` |      |
| `alarmColor`         | `string`  |      |
| `handingPlan`        | `string`  |      |
| `isDefend`           | `integer` |      |
| `alarmStatusVarName` | `string`  |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.3 更新变量告警属性

| 项          | 内容                                       |
| ----------- | ------------------------------------------ |
| 接口路径    | `/alarmVarProperty/updateAlarmVarProperty` |
| 请求方法    | `POST`                                     |
| 前端封装    | `SystemController.updateAlarmVarProperty`  |
| Swagger Tag | alarmVariablePropertyApi                   |
| 作用说明    | 更新变量告警属性                           |

**请求参数（Body）：**

| 字段                 | 类型      | 说明 |
| -------------------- | --------- | ---- |
| `id`                 | `integer` |      |
| `deviceCode`         | `string`  |      |
| `varId`              | `integer` |      |
| `varName`            | `string`  |      |
| `priority`           | `string`  |      |
| `alarmRankId`        | `integer` |      |
| `alarmCategoryId`    | `integer` |      |
| `alarmName`          | `string`  |      |
| `riskLevel`          | `string`  |      |
| `alarmSourceId`      | `integer` |      |
| `alarmColor`         | `string`  |      |
| `handingPlan`        | `string`  |      |
| `isDefend`           | `integer` |      |
| `alarmStatusVarName` | `string`  |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.4 删除变量告警属性

| 项          | 内容                                       |
| ----------- | ------------------------------------------ |
| 接口路径    | `/alarmVarProperty/deleteAlarmVarProperty` |
| 请求方法    | `POST`                                     |
| 前端封装    | `SystemController.deleteAlarmVarProperty`  |
| Swagger Tag | alarmVariablePropertyApi                   |
| 作用说明    | 删除变量告警属性                           |

**请求参数（Body）：**

| 字段                 | 类型      | 说明 |
| -------------------- | --------- | ---- |
| `id`                 | `integer` |      |
| `deviceCode`         | `string`  |      |
| `varId`              | `integer` |      |
| `varName`            | `string`  |      |
| `priority`           | `string`  |      |
| `alarmRankId`        | `integer` |      |
| `alarmCategoryId`    | `integer` |      |
| `alarmName`          | `string`  |      |
| `riskLevel`          | `string`  |      |
| `alarmSourceId`      | `integer` |      |
| `alarmColor`         | `string`  |      |
| `handingPlan`        | `string`  |      |
| `isDefend`           | `integer` |      |
| `alarmStatusVarName` | `string`  |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.5 根据id查询变量告警属性

| 项          | 内容                                        |
| ----------- | ------------------------------------------- |
| 接口路径    | `/alarmVarProperty/getAlarmVarPropertyById` |
| 请求方法    | `POST`                                      |
| 前端封装    | `SystemController.getAlarmVarPropertyById`  |
| Swagger Tag | alarmVariablePropertyApi                    |
| 作用说明    | 根据id查询变量告警属性                      |

**请求参数（Body）：**

| 字段                 | 类型      | 说明 |
| -------------------- | --------- | ---- |
| `id`                 | `integer` |      |
| `deviceCode`         | `string`  |      |
| `varId`              | `integer` |      |
| `varName`            | `string`  |      |
| `priority`           | `string`  |      |
| `alarmRankId`        | `integer` |      |
| `alarmCategoryId`    | `integer` |      |
| `alarmName`          | `string`  |      |
| `riskLevel`          | `string`  |      |
| `alarmSourceId`      | `integer` |      |
| `alarmColor`         | `string`  |      |
| `handingPlan`        | `string`  |      |
| `isDefend`           | `integer` |      |
| `alarmStatusVarName` | `string`  |      |

**响应体：**

| 字段                      | 类型      | 说明 |
| ------------------------- | --------- | ---- |
| `code`                    | `integer` |      |
| `message`                 | `string`  |      |
| `data`                    | `object`  |      |
| `data.id`                 | `integer` |      |
| `data.deviceCode`         | `string`  |      |
| `data.varId`              | `integer` |      |
| `data.varName`            | `string`  |      |
| `data.priority`           | `string`  |      |
| `data.alarmRankId`        | `integer` |      |
| `data.alarmRankName`      | `string`  |      |
| `data.alarmCategoryId`    | `integer` |      |
| `data.alarmCategoryName`  | `string`  |      |
| `data.alarmName`          | `string`  |      |
| `data.riskLevel`          | `string`  |      |
| `data.alarmSourceId`      | `integer` |      |
| `data.alarmSourceName`    | `string`  |      |
| `data.alarmColor`         | `string`  |      |
| `data.handingPlan`        | `string`  |      |
| `data.isDefend`           | `integer` |      |
| `data.alarmStatusVarName` | `string`  |      |
| `data.createdTime`        | `string`  |      |
| `data.updatedTime`        | `string`  |      |

---

### 8.6 导出变量告警属性

| 项          | 内容                                       |
| ----------- | ------------------------------------------ |
| 接口路径    | `/alarmVarProperty/exportAlarmVarProperty` |
| 请求方法    | `GET`                                      |
| 前端封装    | `SystemController.exportAlarmVarProperty`  |
| Swagger Tag | alarmVariablePropertyApi                   |
| 作用说明    | 导出变量告警属性                           |

**Query/Path 参数：**

| 参数名            | 位置  | 必填 | 类型     | 说明 |
| ----------------- | ----- | ---- | -------- | ---- |
| `page`            | query | 是   | `string` |      |
| `size`            | query | 是   | `string` |      |
| `search`          | query | 否   | `string` |      |
| `fieldList[0]`    | query | 否   | `string` |      |
| `sorter[0].order` | query | 否   | `string` |      |
| `sorter[0].field` | query | 否   | `string` |      |
| `varId`           | query | 否   | `string` |      |
| `priority`        | query | 否   | `string` |      |
| `alarmRankId`     | query | 否   | `string` |      |
| `alarmCategoryId` | query | 否   | `string` |      |
| `alarmName`       | query | 否   | `string` |      |
| `riskLevel`       | query | 否   | `string` |      |
| `alarmSourceId`   | query | 否   | `string` |      |
| `alarmColor`      | query | 否   | `string` |      |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

---

### 8.7 导入变量告警属性

| 项          | 内容                                       |
| ----------- | ------------------------------------------ |
| 接口路径    | `/alarmVarProperty/importAlarmVarProperty` |
| 请求方法    | `POST`                                     |
| 前端封装    | `SystemController.importAlarmVarProperty`  |
| Swagger Tag | alarmVariablePropertyApi                   |
| 作用说明    | 导入变量告警属性                           |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.8 批量更新变量告警属性

| 项          | 内容                                            |
| ----------- | ----------------------------------------------- |
| 接口路径    | `/alarmVarProperty/batchUpdateAlarmVarProperty` |
| 请求方法    | `POST`                                          |
| 前端封装    | `SystemController.batchUpdateAlarmVarProperty`  |
| Swagger Tag | alarmVariablePropertyApi                        |
| 作用说明    | 批量更新变量告警属性                            |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.9 获取设备变量列表

| 项          | 内容                                     |
| ----------- | ---------------------------------------- |
| 接口路径    | `/device/getDevicVariableeList`          |
| 请求方法    | `POST`                                   |
| 前端封装    | `SystemController.getDevicVariableeList` |
| Swagger Tag | deviceManagementApi                      |
| 作用说明    | 获取设备变量列表                         |

**请求参数（Body）：**

| 字段              | 类型             | 说明                 |
| ----------------- | ---------------- | -------------------- |
| `page`            | `integer`        |                      |
| `size`            | `integer`        |                      |
| `search`          | `string`         |                      |
| `fieldList`       | `array<string>`  |                      |
| `sorter`          | `array<object>`  |                      |
| `sorter[].order`  | `string`         |                      |
| `sorter[].field`  | `string`         |                      |
| `deviceName`      | `string`         |                      |
| `deviceCode`      | `string`         |                      |
| `deviceGroupId`   | `integer`        |                      |
| `varName`         | `string`         |                      |
| `showName`        | `string`         |                      |
| `varAddress`      | `string`         |                      |
| `deviceCombId`    | `integer`        | 新增组合设备查询     |
| `subSystemId`     | `integer`        | 系只能子系统id查询   |
| `containSubLevel` | `integer`        | 新增是否包含下级查询 |
| `regionId`        | `integer`        |                      |
| `varType`         | `string`         |                      |
| `ids`             | `array<integer>` |                      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.10 获取报警级别字典列表

| 项          | 内容                                |
| ----------- | ----------------------------------- |
| 接口路径    | `/dic/getAlarmRankList`             |
| 请求方法    | `POST`                              |
| 前端封装    | `SystemController.getAlarmRankList` |
| Swagger Tag | dictionaryApi                       |
| 作用说明    | 获取报警级别字典列表                |

**请求参数（Body）：**

| 字段        | 类型            | 说明 |
| ----------- | --------------- | ---- |
| `page`      | `integer`       |      |
| `size`      | `integer`       |      |
| `search`    | `string`        |      |
| `fieldList` | `array<string>` |      |

**响应体：**

| 字段                     | 类型            | 说明         |
| ------------------------ | --------------- | ------------ |
| `code`                   | `integer`       |              |
| `message`                | `string`        |              |
| `data`                   | `array<object>` |              |
| `data[].id`              | `integer`       |              |
| `data[].alarmLevelStyle` | `string`        | 全域告警新增 |
| `data[].remark`          | `string`        |              |
| `data[].createdTime`     | `string`        |              |
| `data[].updatedTime`     | `string`        |              |
| `data[].name`            | `string`        |              |

---

### 8.11 获取报警类别字典列表

| 项          | 内容                                    |
| ----------- | --------------------------------------- |
| 接口路径    | `/dic/getAlarmCategoryList`             |
| 请求方法    | `POST`                                  |
| 前端封装    | `SystemController.getAlarmCategoryList` |
| Swagger Tag | dictionaryApi                           |
| 作用说明    | 获取报警类别字典列表                    |

**请求参数（Body）：**

| 字段        | 类型            | 说明 |
| ----------- | --------------- | ---- |
| `page`      | `integer`       |      |
| `size`      | `integer`       |      |
| `search`    | `string`        |      |
| `fieldList` | `array<string>` |      |

**响应体：**

| 字段                        | 类型            | 说明         |
| --------------------------- | --------------- | ------------ |
| `code`                      | `integer`       |              |
| `message`                   | `string`        |              |
| `data`                      | `array<object>` |              |
| `data[].id`                 | `integer`       |              |
| `data[].alarmCategoryStyle` | `string`        | 全域告警新增 |
| `data[].remark`             | `string`        |              |
| `data[].createdTime`        | `string`        |              |
| `data[].updatedTime`        | `string`        |              |
| `data[].name`               | `string`        |              |

---

### 8.12 获取报警源字典列表

| 项          | 内容                                  |
| ----------- | ------------------------------------- |
| 接口路径    | `/dic/getAlarmSourceList`             |
| 请求方法    | `POST`                                |
| 前端封装    | `SystemController.getAlarmSourceList` |
| Swagger Tag | dictionaryApi                         |
| 作用说明    | 获取报警源字典列表                    |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段                 | 类型            | 说明 |
| -------------------- | --------------- | ---- |
| `code`               | `integer`       |      |
| `message`            | `string`        |      |
| `data`               | `array<object>` |      |
| `data[].id`          | `integer`       |      |
| `data[].name`        | `string`        |      |
| `data[].remark`      | `string`        |      |
| `data[].createdTime` | `string`        |      |
| `data[].updatedTime` | `string`        |      |

---

### 8.13 checkAviatorScript

| 项       | 内容                                  |
| -------- | ------------------------------------- |
| 接口路径 | `/aviator/checkAviatorScript`         |
| 请求方法 | `POST`                                |
| 前端封装 | `SystemController.checkAviatorScript` |
| 作用说明 | 见模块业务逻辑                        |

_未在平台 OpenAPI 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---

### 8.14 获取设备分组树

| 项          | 内容                                  |
| ----------- | ------------------------------------- |
| 接口路径    | `/device/getDeviceGroupTree`          |
| 请求方法    | `POST`                                |
| 前端封装    | `SystemController.getDeviceGroupTree` |
| Swagger Tag | deviceManagementApi                   |
| 作用说明    | 获取设备分组树                        |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段         | 类型            | 说明 |
| ------------ | --------------- | ---- |
| `code`       | `integer`       |      |
| `message`    | `string`        |      |
| `data`       | `array<object>` |      |
| `data[].key` | `object`        |      |

---

### 8.15 获取菜单树

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

### 8.16 查询组合设备和关联列表

| 项          | 内容                                 |
| ----------- | ------------------------------------ |
| 接口路径    | `/deviceComb/getDeviceCombList`      |
| 请求方法    | `POST`                               |
| 前端封装    | `SystemController.getDeviceCombList` |
| Swagger Tag | deviceCombinationApi                 |
| 作用说明    | 查询组合设备和关联列表               |

**请求参数（Body）：**

| 字段        | 类型            | 说明 |
| ----------- | --------------- | ---- |
| `page`      | `integer`       |      |
| `size`      | `integer`       |      |
| `search`    | `string`        |      |
| `fieldList` | `array<string>` |      |
| `name`      | `string`        |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.17 获取设备列表

| 项          | 内容                             |
| ----------- | -------------------------------- |
| 接口路径    | `/device/getDeviceList`          |
| 请求方法    | `POST`                           |
| 前端封装    | `SystemController.getDeviceList` |
| Swagger Tag | deviceManagementApi              |
| 作用说明    | 获取设备列表                     |

**请求参数（Body）：**

| 字段              | 类型             | 说明                                       |
| ----------------- | ---------------- | ------------------------------------------ |
| `page`            | `integer`        |                                            |
| `size`            | `integer`        |                                            |
| `search`          | `string`         |                                            |
| `fieldList`       | `array<string>`  |                                            |
| `sorter`          | `array<object>`  |                                            |
| `sorter[].order`  | `string`         |                                            |
| `sorter[].field`  | `string`         |                                            |
| `deviceCode`      | `string`         |                                            |
| `deviceName`      | `string`         |                                            |
| `deviceGroupId`   | `integer`        |                                            |
| `subSystemId`     | `integer`        |                                            |
| `regionId`        | `integer`        |                                            |
| `deviceStatus`    | `integer`        |                                            |
| `onlineStatus`    | `integer`        |                                            |
| `commDeviceId`    | `integer`        |                                            |
| `collectServerId` | `integer`        |                                            |
| `deviceCombId`    | `integer`        | 新增组合设备查询                           |
| `isTemplate`      | `integer`        | 新增是否模板设备查询                       |
| `containSubLevel` | `integer`        | 新增是否包含下级查询                       |
| `commModel`       | `array<integer>` | 新增通信模式字段（1-直接，2-间接，3-网关） |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.18 getValueTypeList

| 项       | 内容                                |
| -------- | ----------------------------------- |
| 接口路径 | `/dic/getValueTypeList`             |
| 请求方法 | `GET`                               |
| 前端封装 | `SystemController.getValueTypeList` |
| 作用说明 | 见模块业务逻辑                      |

_未在平台 OpenAPI 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---

### 8.19 变量类型枚举

| 项          | 内容                              |
| ----------- | --------------------------------- |
| 接口路径    | `/device/getVarTypeEnum`          |
| 请求方法    | `GET`                             |
| 前端封装    | `SystemController.getVarTypeEnum` |
| Swagger Tag | deviceManagementApi               |
| 作用说明    | 变量类型枚举                      |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段         | 类型            | 说明 |
| ------------ | --------------- | ---- |
| `code`       | `integer`       |      |
| `message`    | `string`        |      |
| `data`       | `array<object>` |      |
| `data[].key` | `string`        |      |

---
