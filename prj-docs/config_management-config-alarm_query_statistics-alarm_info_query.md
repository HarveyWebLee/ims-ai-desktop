# 告警信息查询（alarm_info_query）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                                         |
| ------------------ | ---------------------------------------------------------------------------- |
| 模块名称（中文）   | 告警信息查询                                                                 |
| 模块名称（英文）   | Alarm Info Query                                                             |
| 所属 Group（中文） | 告警查询统计                                                                 |
| 所属 Group（英文） | Alarm Query Statistics                                                       |
| Group ID           | `alarm_query_statistics`                                                     |
| 菜单位置           | 配置管理平台 → 配置管理 → 告警查询统计 → 告警信息查询                        |
| 路由路径           | `/config_management/config/alarm_query_statistics/alarm_info_query`          |
| 页面目录           | `src/pages/config_management/config/alarm_query_statistics/alarm_info_query` |

## 1. 模块定位与项目作用

告警信息查询是综合信息平台中「告警查询统计」业务域下的功能模块，对应页面目录 `src/pages/config_management/config/alarm_query_statistics/alarm_info_query`。

在项目中的主要作用：

- 作为「配置管理平台 → 配置管理 → 告警查询统计 → 告警信息查询」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
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

| 字段名            | 中文含义     | 作用说明                        |
| ----------------- | ------------ | ------------------------------- |
| id                | 报警事件名称 | 模块表单/列表字段，详见页面配置 |
| deviceName        | 防区         | 模块表单/列表字段，详见页面配置 |
| defenceAreaName   | 设备属性     | 模块表单/列表字段，详见页面配置 |
| alarmRankName     | 报警信息     | 模块表单/列表字段，详见页面配置 |
| statusName        | 开始时间     | 模块表单/列表字段，详见页面配置 |
| faultCode         | 确认人       | 模块表单/列表字段，详见页面配置 |
| variableNames     | 设备属性     | 模块表单/列表字段，详见页面配置 |
| eventName         | 报警事件名称 | 模块表单/列表字段，详见页面配置 |
| subSystemId       | 所属子系统   | 模块表单/列表字段，详见页面配置 |
| subSystemName     | 所属子系统   | 模块表单/列表字段，详见页面配置 |
| deviceCodes       | 监控设备     | 模块表单/列表字段，详见页面配置 |
| deviceVarName     | 设备属性     | 模块表单/列表字段，详见页面配置 |
| alarmValue        | 报警值       | 模块表单/列表字段，详见页面配置 |
| calibrationValue  | 标定值       | 模块表单/列表字段，详见页面配置 |
| createdTime       | 入库时间     | 模块表单/列表字段，详见页面配置 |
| startTime         | 开始时间     | 模块表单/列表字段，详见页面配置 |
| endTime           | 结束时间     | 模块表单/列表字段，详见页面配置 |
| alarmRankId       | 报警级别     | 模块表单/列表字段，详见页面配置 |
| alarmCategoryId   | 报警类型     | 模块表单/列表字段，详见页面配置 |
| alarmCategoryName | 报警类别     | 模块表单/列表字段，详见页面配置 |
| status            | 报警状态     | 模块表单/列表字段，详见页面配置 |
| time              | 开始时间     | 模块表单/列表字段，详见页面配置 |
| confirmPerson     | 确认人       | 模块表单/列表字段，详见页面配置 |
| confirmTime       | 确认时间     | 模块表单/列表字段，详见页面配置 |
| processPerson     | 处理人       | 模块表单/列表字段，详见页面配置 |
| processTime       | 处理时间     | 模块表单/列表字段，详见页面配置 |
| handleMethod      | 处理方法     | 模块表单/列表字段，详见页面配置 |
| 修改              | 修改         | 模块表单/列表字段，详见页面配置 |
| 保存              | 保存         | 模块表单/列表字段，详见页面配置 |
| 列表              | 列表         | 模块表单/列表字段，详见页面配置 |
| 取消              | 取消         | 模块表单/列表字段，详见页面配置 |
| 批量删除          | 批量删除     | 模块表单/列表字段，详见页面配置 |
| 批量确认          | 批量确认     | 模块表单/列表字段，详见页面配置 |
| 批量处理          | 批量处理     | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

- 新建/新增
- 编辑
- 删除
- 详情回填
- 导出
- 导入
- 左侧树筛选
- 启用/停用

---

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                              | 关系说明                                         |
| ------------------------------------- | ------------------------------------------------ |
| 告警信息统计（alarm_info_statistics） | 同级功能模块，可共同构成「告警查询统计」业务能力 |

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

本模块（`alarm_info_query`）位于 `src/pages/config_management/config/alarm_query_statistics/alarm_info_query`，归属「告警查询统计」。它负责「告警信息查询」相关业务的页面交互与数据读写。维护本模块时，请同步关注接口契约、字段语义及与兄弟模块的数据一致性。

---

## 8. 接口清单

以下接口由本模块页面代码直接或通过 `@/services` Controller 调用，参数与响应 Schema 来自 `swaggerApi.json`（若可匹配）。

### 8.1 获取告警记录列表

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

### 8.2 导出告警记录

| 项          | 内容                           |
| ----------- | ------------------------------ |
| 接口路径    | `/alarm/exportAlarm`           |
| 请求方法    | `GET`                          |
| 前端封装    | `SystemController.exportAlarm` |
| Swagger Tag | alarmManagementApi             |
| 作用说明    | 导出告警记录                   |

**Query/Path 参数：**

| 参数名             | 位置  | 必填 | 类型     | 说明             |
| ------------------ | ----- | ---- | -------- | ---------------- |
| `page`             | query | 是   | `string` |                  |
| `size`             | query | 是   | `string` |                  |
| `search`           | query | 否   | `string` |                  |
| `fieldList[0]`     | query | 否   | `string` |                  |
| `sorter[0].order`  | query | 否   | `string` |                  |
| `sorter[0].field`  | query | 否   | `string` |                  |
| `subSystemId`      | query | 否   | `string` |                  |
| `alarmCategoryId`  | query | 否   | `string` |                  |
| `alarmRankId`      | query | 否   | `string` |                  |
| `status`           | query | 否   | `string` |                  |
| `startTime`        | query | 否   | `string` |                  |
| `endTime`          | query | 否   | `string` |                  |
| `deviceCombId`     | query | 否   | `string` | 新增组合设备查询 |
| `regionId`         | query | 否   | `string` | 区域id           |
| `isIncludeSub`     | query | 否   | `string` | 是否包含下级     |
| `deviceCodes[0]`   | query | 否   | `string` | 新增设备编码集合 |
| `variableNames[0]` | query | 否   | `string` | 新增变量名称集合 |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

---

### 8.3 更新告警记录

| 项          | 内容                           |
| ----------- | ------------------------------ |
| 接口路径    | `/alarm/updateAlarm`           |
| 请求方法    | `POST`                         |
| 前端封装    | `SystemController.updateAlarm` |
| Swagger Tag | alarmManagementApi             |
| 作用说明    | 更新告警记录                   |

**请求参数（Body）：**

| 字段               | 类型             | 说明                   |
| ------------------ | ---------------- | ---------------------- |
| `id`               | `integer`        |                        |
| `eventName`        | `string`         |                        |
| `localCode`        | `string`         | 本地系统编码           |
| `eventCode`        | `string`         | 子系统编码             |
| `deviceId`         | `integer`        |                        |
| `deviceCode`       | `string`         |                        |
| `deviceVarId`      | `integer`        |                        |
| `alarmValue`       | `string`         |                        |
| `calibrationValue` | `string`         |                        |
| `startTime`        | `string`         |                        |
| `endTime`          | `string`         |                        |
| `alarmCategoryId`  | `integer`        |                        |
| `alarmRankId`      | `integer`        |                        |
| `faultCode`        | `string`         |                        |
| `status`           | `integer`        |                        |
| `confirmPerson`    | `string`         |                        |
| `confirmTime`      | `string`         |                        |
| `processPerson`    | `string`         |                        |
| `processTime`      | `string`         |                        |
| `regionId`         | `integer`        | 区域信息（设备的属性） |
| `subSystemId`      | `integer`        |                        |
| `priority`         | `string`         | 全域告警新增属性       |
| `riskLevel`        | `string`         |                        |
| `alarmSourceId`    | `integer`        |                        |
| `alarmColor`       | `string`         |                        |
| `ids`              | `array<integer>` |                        |
| `defenceAreaId`    | `integer`        |                        |
| `tableName`        | `string`         | 新增表名               |
| `handleMethod`     | `string`         | 新增处理方法           |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.4 删除告警记录

| 项          | 内容                           |
| ----------- | ------------------------------ |
| 接口路径    | `/alarm/deleteAlarm`           |
| 请求方法    | `POST`                         |
| 前端封装    | `SystemController.deleteAlarm` |
| Swagger Tag | alarmManagementApi             |
| 作用说明    | 删除告警记录                   |

**请求参数（Body）：**

| 字段                      | 类型             | 说明                   |
| ------------------------- | ---------------- | ---------------------- |
| `root`                    | `array`          |                        |
| `item[].id`               | `integer`        |                        |
| `item[].eventName`        | `string`         |                        |
| `item[].localCode`        | `string`         | 本地系统编码           |
| `item[].eventCode`        | `string`         | 子系统编码             |
| `item[].deviceId`         | `integer`        |                        |
| `item[].deviceCode`       | `string`         |                        |
| `item[].deviceVarId`      | `integer`        |                        |
| `item[].alarmValue`       | `string`         |                        |
| `item[].calibrationValue` | `string`         |                        |
| `item[].startTime`        | `string`         |                        |
| `item[].endTime`          | `string`         |                        |
| `item[].alarmCategoryId`  | `integer`        |                        |
| `item[].alarmRankId`      | `integer`        |                        |
| `item[].faultCode`        | `string`         |                        |
| `item[].status`           | `integer`        |                        |
| `item[].confirmPerson`    | `string`         |                        |
| `item[].confirmTime`      | `string`         |                        |
| `item[].processPerson`    | `string`         |                        |
| `item[].processTime`      | `string`         |                        |
| `item[].regionId`         | `integer`        | 区域信息（设备的属性） |
| `item[].subSystemId`      | `integer`        |                        |
| `item[].priority`         | `string`         | 全域告警新增属性       |
| `item[].riskLevel`        | `string`         |                        |
| `item[].alarmSourceId`    | `integer`        |                        |
| `item[].alarmColor`       | `string`         |                        |
| `item[].ids`              | `array<integer>` |                        |
| `item[].defenceAreaId`    | `integer`        |                        |
| `item[].tableName`        | `string`         | 新增表名               |
| `item[].handleMethod`     | `string`         | 新增处理方法           |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.5 获取菜单树

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

### 8.6 确认操作

| 项          | 内容                            |
| ----------- | ------------------------------- |
| 接口路径    | `/alarm/confirmAlarm`           |
| 请求方法    | `POST`                          |
| 前端封装    | `SystemController.confirmAlarm` |
| Swagger Tag | alarmManagementApi              |
| 作用说明    | 确认操作                        |

**请求参数（Body）：**

| 字段                      | 类型             | 说明                   |
| ------------------------- | ---------------- | ---------------------- |
| `root`                    | `array`          |                        |
| `item[].id`               | `integer`        |                        |
| `item[].eventName`        | `string`         |                        |
| `item[].localCode`        | `string`         | 本地系统编码           |
| `item[].eventCode`        | `string`         | 子系统编码             |
| `item[].deviceId`         | `integer`        |                        |
| `item[].deviceCode`       | `string`         |                        |
| `item[].deviceVarId`      | `integer`        |                        |
| `item[].alarmValue`       | `string`         |                        |
| `item[].calibrationValue` | `string`         |                        |
| `item[].startTime`        | `string`         |                        |
| `item[].endTime`          | `string`         |                        |
| `item[].alarmCategoryId`  | `integer`        |                        |
| `item[].alarmRankId`      | `integer`        |                        |
| `item[].faultCode`        | `string`         |                        |
| `item[].status`           | `integer`        |                        |
| `item[].confirmPerson`    | `string`         |                        |
| `item[].confirmTime`      | `string`         |                        |
| `item[].processPerson`    | `string`         |                        |
| `item[].processTime`      | `string`         |                        |
| `item[].regionId`         | `integer`        | 区域信息（设备的属性） |
| `item[].subSystemId`      | `integer`        |                        |
| `item[].priority`         | `string`         | 全域告警新增属性       |
| `item[].riskLevel`        | `string`         |                        |
| `item[].alarmSourceId`    | `integer`        |                        |
| `item[].alarmColor`       | `string`         |                        |
| `item[].ids`              | `array<integer>` |                        |
| `item[].defenceAreaId`    | `integer`        |                        |
| `item[].tableName`        | `string`         | 新增表名               |
| `item[].handleMethod`     | `string`         | 新增处理方法           |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.7 处理操作

| 项          | 内容                            |
| ----------- | ------------------------------- |
| 接口路径    | `/alarm/processAlarm`           |
| 请求方法    | `POST`                          |
| 前端封装    | `SystemController.processAlarm` |
| Swagger Tag | alarmManagementApi              |
| 作用说明    | 处理操作                        |

**请求参数（Body）：**

| 字段                      | 类型             | 说明                   |
| ------------------------- | ---------------- | ---------------------- |
| `root`                    | `array`          |                        |
| `item[].id`               | `integer`        |                        |
| `item[].eventName`        | `string`         |                        |
| `item[].localCode`        | `string`         | 本地系统编码           |
| `item[].eventCode`        | `string`         | 子系统编码             |
| `item[].deviceId`         | `integer`        |                        |
| `item[].deviceCode`       | `string`         |                        |
| `item[].deviceVarId`      | `integer`        |                        |
| `item[].alarmValue`       | `string`         |                        |
| `item[].calibrationValue` | `string`         |                        |
| `item[].startTime`        | `string`         |                        |
| `item[].endTime`          | `string`         |                        |
| `item[].alarmCategoryId`  | `integer`        |                        |
| `item[].alarmRankId`      | `integer`        |                        |
| `item[].faultCode`        | `string`         |                        |
| `item[].status`           | `integer`        |                        |
| `item[].confirmPerson`    | `string`         |                        |
| `item[].confirmTime`      | `string`         |                        |
| `item[].processPerson`    | `string`         |                        |
| `item[].processTime`      | `string`         |                        |
| `item[].regionId`         | `integer`        | 区域信息（设备的属性） |
| `item[].subSystemId`      | `integer`        |                        |
| `item[].priority`         | `string`         | 全域告警新增属性       |
| `item[].riskLevel`        | `string`         |                        |
| `item[].alarmSourceId`    | `integer`        |                        |
| `item[].alarmColor`       | `string`         |                        |
| `item[].ids`              | `array<integer>` |                        |
| `item[].defenceAreaId`    | `integer`        |                        |
| `item[].tableName`        | `string`         | 新增表名               |
| `item[].handleMethod`     | `string`         | 新增处理方法           |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.8 获取报警类别字典列表

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

### 8.9 筛选出不同设备都拥有的设备变量英文名

| 项          | 内容                                 |
| ----------- | ------------------------------------ |
| 接口路径    | `/device/getSameVarName`             |
| 请求方法    | `POST`                               |
| 前端封装    | `SystemController.getSameVarName`    |
| baseURL     | `/openapi/app`                       |
| Swagger Tag | deviceManagementApi                  |
| 作用说明    | 筛选出不同设备都拥有的设备变量英文名 |

**请求参数（Body）：**

| 字段   | 类型    | 说明 |
| ------ | ------- | ---- |
| `root` | `array` |      |

**响应体：**

| 字段      | 类型            | 说明 |
| --------- | --------------- | ---- |
| `code`    | `integer`       |      |
| `message` | `string`        |      |
| `data`    | `array<string>` |      |

---

### 8.10 获取设备列表

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

### 8.11 获取报警级别字典列表

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
