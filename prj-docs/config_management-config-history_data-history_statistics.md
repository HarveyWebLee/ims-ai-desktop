# 历史曲线查询（history_statistics）知识库

> 上级模块索引：[history_data.md](./history_data.md) · 总索引：[README.md](./README.md) · 页面总表：[TOTAL-MODULE.md](./TOTAL-MODULE.md)

## 0. 路由与归属信息

| 项                 | 内容                                                                 |
| ------------------ | -------------------------------------------------------------------- |
| 模块名称（中文）   | 历史曲线查询                                                         |
| 模块名称（英文）   | History Statistics                                                   |
| 所属 Group（中文） | 历史数据查询统计                                                     |
| 所属 Group（英文） | History Data Query Statistics                                        |
| Group ID           | `history_data`                                                       |
| 菜单位置           | 配置管理平台 → 配置管理 → 历史数据查询统计 → 历史曲线查询            |
| 路由路径           | `/config_management/config/history_statistics`                       |
| 页面目录           | `src/pages/config_management/config/history_data/history_statistics` |

## 1. 模块定位与项目作用

历史数据统计是综合信息平台中「历史数据查询统计」业务域下的功能模块，对应页面目录 `src/pages/config_management/config/history_data/history_statistics`。

在项目中的主要作用：

- 作为「配置管理平台 → 配置管理 → 历史数据 → 历史数据统计」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
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

| 字段名      | 中文含义     | 作用说明                        |
| ----------- | ------------ | ------------------------------- |
| subSystemId | 所属子系统   | 模块表单/列表字段，详见页面配置 |
| devNoList   | 监控设备     | 模块表单/列表字段，详见页面配置 |
| varNo       | 设备变量     | 模块表单/列表字段，详见页面配置 |
| time        | 记录时间     | 模块表单/列表字段，详见页面配置 |
| devShowName | 监控设备     | 模块表单/列表字段，详见页面配置 |
| dn          | 设备编号     | 模块表单/列表字段，详见页面配置 |
| varShowName | 变量中文名称 | 模块表单/列表字段，详见页面配置 |
| vn          | 变量英文名称 | 模块表单/列表字段，详见页面配置 |
| tsFormat    | 记录时间     | 模块表单/列表字段，详见页面配置 |
| vv          | 记录值       | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

- 导出
- 导入
- 左侧树筛选
- 启用/停用

---

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                                     | 关系说明                                             |
| -------------------------------------------- | ---------------------------------------------------- |
| 设备注册索引（device_registry_index）        | 同级功能模块，可共同构成「历史数据查询统计」业务能力 |
| 历史数据修复（history_data_repair）          | 同级功能模块，可共同构成「历史数据查询统计」业务能力 |
| 历史数据查询（history_query）                | 同级功能模块，可共同构成「历史数据查询统计」业务能力 |
| 查询模板配置（query_template_configuration） | 同级功能模块，可共同构成「历史数据查询统计」业务能力 |
| 任务管理（task_manage）                      | 同级功能模块，可共同构成「历史数据查询统计」业务能力 |

### 5.2 上游依赖 / 下游消费

- **上游**：根据本页接口与字段引用，上游主要为：监控设备（`monitor_equipment`）、用户及参数管理（`user`）、基础数据（`basedata`）。另可能依赖登录会话与菜单授权（用户及参数管理）。
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

本模块（`history_statistics`）位于 `src/pages/config_management/config/history_data/history_statistics`，归属「历史数据查询统计」。它负责「历史数据统计」相关业务的页面交互与数据读写。维护本模块时，请同步关注接口契约、字段语义及与兄弟模块的数据一致性。

---

## 8. 接口清单

以下接口由本模块页面代码直接或通过 `@/services` Controller 调用，参数与响应 Schema 来自平台 OpenAPI（若可匹配）。

### 8.1 获取设备列表

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

### 8.2 根据设备编码获取所有变量信息

| 项          | 内容                                |
| ----------- | ----------------------------------- |
| 接口路径    | `/device/getVarListByCode`          |
| 请求方法    | `POST`                              |
| 前端封装    | `SystemController.getVarListByCode` |
| Swagger Tag | deviceManagementApi                 |
| 作用说明    | 根据设备编码获取所有变量信息        |

**请求参数（Body）：**

| 字段                   | 类型             | 说明                       |
| ---------------------- | ---------------- | -------------------------- |
| `id`                   | `integer`        |                            |
| `deviceCode`           | `string`         |                            |
| `deviceId`             | `integer`        |                            |
| `deviceName`           | `string`         |                            |
| `deviceGroupId`        | `integer`        | private String deviceType; |
| `dataTypeId`           | `integer`        |                            |
| `varName`              | `string`         |                            |
| `showName`             | `string`         |                            |
| `valueTypeId`          | `integer`        |                            |
| `showPrecision`        | `integer`        |                            |
| `maxValue`             | `string`         |                            |
| `minValue`             | `string`         |                            |
| `varAddress`           | `string`         |                            |
| `blockAddress`         | `string`         |                            |
| `byteOrderId`          | `integer`        |                            |
| `varCodeId`            | `integer`        |                            |
| `subAddress`           | `string`         |                            |
| `calibrationValue`     | `string`         |                            |
| `isWrite`              | `integer`        |                            |
| `isRead`               | `integer`        |                            |
| `convertFormula`       | `string`         |                            |
| `timeInterval`         | `integer`        |                            |
| `storeStrategy`        | `string`         |                            |
| `isInside`             | `integer`        |                            |
| `isOut`                | `integer`        |                            |
| `registerTypeId`       | `integer`        |                            |
| `statisticsCategoryId` | `integer`        |                            |
| `unitLength`           | `integer`        |                            |
| `unit`                 | `string`         | 新增变量单位               |
| `resolution`           | `string`         | 分辨率                     |
| `positionValue`        | `string`         |                            |
| `remark`               | `string`         |                            |
| `ids`                  | `array<integer>` |                            |
| `dic1`                 | `string`         | 新增两个字典               |
| `dic2`                 | `string`         |                            |
| `alias`                | `string`         | 新增变量别名，只供展示使用 |
| `pushFrequency`        | `integer`        | 新增推送频率字段           |
| `varType`              | `string`         | 新增变量类型字段           |
| `varParam`             | `string`         |                            |
| `oldVarParam`          | `string`         |                            |
| `varRule`              | `string`         |                            |
| `varRuleInterval`      | `integer`        |                            |
| `luaText`              | `string`         | 新增lua脚本                |
| `filterMode`           | `integer`        | 新增数据过滤字段           |
| `diffValue`            | `string`         |                            |
| `changeRate`           | `string`         |                            |

**响应体：**

| 字段                          | 类型            | 说明                                   |
| ----------------------------- | --------------- | -------------------------------------- |
| `code`                        | `integer`       |                                        |
| `message`                     | `string`        |                                        |
| `data`                        | `array<object>` |                                        |
| `data[].id`                   | `integer`       |                                        |
| `data[].deviceCode`           | `string`        |                                        |
| `data[].deviceId`             | `integer`       |                                        |
| `data[].deviceName`           | `string`        |                                        |
| `data[].deviceGroupId`        | `integer`       | private String deviceType;             |
| `data[].dataTypeId`           | `integer`       |                                        |
| `data[].varName`              | `string`        |                                        |
| `data[].showName`             | `string`        |                                        |
| `data[].valueTypeId`          | `integer`       |                                        |
| `data[].showPrecision`        | `integer`       |                                        |
| `data[].maxValue`             | `string`        |                                        |
| `data[].minValue`             | `string`        |                                        |
| `data[].varAddress`           | `string`        |                                        |
| `data[].blockAddress`         | `string`        |                                        |
| `data[].byteOrderId`          | `integer`       |                                        |
| `data[].varCodeId`            | `integer`       |                                        |
| `data[].subAddress`           | `string`        |                                        |
| `data[].calibrationValue`     | `string`        |                                        |
| `data[].isWrite`              | `integer`       |                                        |
| `data[].isRead`               | `integer`       |                                        |
| `data[].convertFormula`       | `string`        |                                        |
| `data[].timeInterval`         | `integer`       |                                        |
| `data[].storeStrategy`        | `string`        | todo 2025-09-11 存储策略字段改为string |
| `data[].isInside`             | `integer`       |                                        |
| `data[].isOut`                | `integer`       |                                        |
| `data[].registerTypeId`       | `integer`       |                                        |
| `data[].statisticsCategoryId` | `integer`       |                                        |
| `data[].unitLength`           | `integer`       |                                        |
| `data[].positionValue`        | `string`        |                                        |
| `data[].remark`               | `string`        |                                        |
| `data[].dic1`                 | `string`        | 新增两个字典                           |
| `data[].dic2`                 | `string`        |                                        |
| `data[].unit`                 | `string`        | 新增变量单位                           |
| `data[].resolution`           | `string`        | 分辨率                                 |
| `data[].alias`                | `string`        | 新增变量别名，只供展示使用             |
| `data[].pushFrequency`        | `integer`       | 新增推送频率字段                       |
| `data[].varType`              | `string`        | 新增变量类型字段                       |
| `data[].varParam`             | `string`        |                                        |
| `data[].varRule`              | `string`        |                                        |
| `data[].varRuleInterval`      | `integer`       |                                        |
| `data[].luaText`              | `string`        | 新增lua脚本                            |
| `data[].filterMode`           | `integer`       | 新增数据过滤字段                       |
| `data[].diffValue`            | `string`        |                                        |
| `data[].changeRate`           | `string`        |                                        |
| `data[].createdTime`          | `string`        |                                        |
| `data[].updatedTime`          | `string`        |                                        |

---

### 8.3 分页查询历史数据（精简）

| 项          | 内容                                          |
| ----------- | --------------------------------------------- |
| 接口路径    | `/api/app/sysMonitor/getDevDataSimpleList`    |
| 请求方法    | `POST`                                        |
| 前端封装    | `SystemController.getDeviceHistoryRecordPage` |
| Swagger Tag | appGatewayApi                                 |
| 作用说明    | 分页查询历史数据（精简）                      |

**Query/Path 参数：**

| 参数名     | 位置  | 必填 | 类型     | 说明 |
| ---------- | ----- | ---- | -------- | ---- |
| `id`       | query | 否   | `string` |      |
| `username` | query | 否   | `string` |      |
| `realname` | query | 否   | `string` |      |
| `roleName` | query | 否   | `string` |      |

**请求参数（Body）：**

| 字段                                      | 类型            | 说明                                                                                                |
| ----------------------------------------- | --------------- | --------------------------------------------------------------------------------------------------- |
| `startTime`                               | `string`        |                                                                                                     |
| `endTime`                                 | `string`        |                                                                                                     |
| `devNoList`                               | `array<object>` | 设备列表，每个设备包含设备编号和变量列表 如果某个设备的变量列表为空或null，则查询该设备下的所有变量 |
| `devNoList[].devCode`                     | `string`        |                                                                                                     |
| `devNoList[].devShowName`                 | `string`        |                                                                                                     |
| `devNoList[].deviceVarList`               | `array<object>` |                                                                                                     |
| `devNoList[].deviceVarList[].varCode`     | `string`        |                                                                                                     |
| `devNoList[].deviceVarList[].varShowName` | `string`        |                                                                                                     |
| `page`                                    | `integer`       |                                                                                                     |
| `size`                                    | `integer`       |                                                                                                     |
| `taskNo`                                  | `string`        |                                                                                                     |

**响应体：**

| 字段                      | 类型            | 说明 |
| ------------------------- | --------------- | ---- |
| `code`                    | `integer`       |      |
| `message`                 | `string`        |      |
| `data`                    | `object`        |      |
| `data.current`            | `integer`       |      |
| `data.pages`              | `integer`       |      |
| `data.size`               | `integer`       |      |
| `data.total`              | `integer`       |      |
| `data.records`            | `array<object>` |      |
| `data.records[].tsFormat` | `string`        |      |
| `data.records[].ts`       | `integer`       |      |
| `data.records[].vv`       | `string`        |      |

---

### 8.4 获取菜单树

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

### 8.5 筛选出不同设备都拥有的设备变量英文名

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

### 8.6 获取历史数据曲线接口

| 项          | 内容                                   |
| ----------- | -------------------------------------- |
| 接口路径    | `/sysMonitor/getDevVarDataList`        |
| 请求方法    | `POST`                                 |
| 前端封装    | `SystemController.getHistoryCurveData` |
| Swagger Tag | systemMonitorApi                       |
| 作用说明    | 获取历史数据曲线接口                   |

**Query/Path 参数：**

| 参数名     | 位置  | 必填 | 类型     | 说明 |
| ---------- | ----- | ---- | -------- | ---- |
| `id`       | query | 否   | `string` |      |
| `username` | query | 否   | `string` |      |
| `realname` | query | 否   | `string` |      |
| `roleName` | query | 否   | `string` |      |

**请求参数（Body）：**

| 字段                                      | 类型            | 说明                                                                                                |
| ----------------------------------------- | --------------- | --------------------------------------------------------------------------------------------------- |
| `startTime`                               | `string`        |                                                                                                     |
| `endTime`                                 | `string`        |                                                                                                     |
| `devNoList`                               | `array<object>` | 设备列表，每个设备包含设备编号和变量列表 如果某个设备的变量列表为空或null，则查询该设备下的所有变量 |
| `devNoList[].devCode`                     | `string`        |                                                                                                     |
| `devNoList[].devShowName`                 | `string`        |                                                                                                     |
| `devNoList[].deviceVarList`               | `array<object>` |                                                                                                     |
| `devNoList[].deviceVarList[].varCode`     | `string`        |                                                                                                     |
| `devNoList[].deviceVarList[].varShowName` | `string`        |                                                                                                     |
| `page`                                    | `integer`       |                                                                                                     |
| `size`                                    | `integer`       |                                                                                                     |
| `taskNo`                                  | `string`        |                                                                                                     |

**响应体：**

| 字段                                  | 类型            | 说明 |
| ------------------------------------- | --------------- | ---- |
| `code`                                | `integer`       |      |
| `message`                             | `string`        |      |
| `data`                                | `array<object>` |      |
| `data[].devShowName`                  | `string`        |      |
| `data[].dn`                           | `string`        |      |
| `data[].varShowName`                  | `string`        |      |
| `data[].vn`                           | `string`        |      |
| `data[].deviceDataList`               | `array<object>` |      |
| `data[].deviceDataList[].devShowName` | `string`        |      |
| `data[].deviceDataList[].varShowName` | `string`        |      |
| `data[].deviceDataList[].tsFormat`    | `string`        |      |
| `data[].deviceDataList[].id`          | `integer`       |      |
| `data[].deviceDataList[].ts`          | `integer`       |      |
| `data[].deviceDataList[].mid`         | `string`        |      |
| `data[].deviceDataList[].dn`          | `string`        |      |
| `data[].deviceDataList[].dt`          | `string`        |      |
| `data[].deviceDataList[].vn`          | `string`        |      |
| `data[].deviceDataList[].vt`          | `string`        |      |
| `data[].deviceDataList[].vv`          | `string`        |      |
| `data[].deviceDataList[].vcv`         | `string`        |      |
| `data[].deviceDataList[].ct`          | `string`        |      |

---
