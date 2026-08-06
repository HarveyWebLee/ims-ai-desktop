# 库房统计（storage_statistics）知识库

## 0. 路由与归属信息

| 项                 | 内容                           |
| ------------------ | ------------------------------ |
| 模块名称（中文）   | 库房统计                       |
| 模块名称（英文）   | Storage Statistics             |
| 所属 Group（中文） | 库房统计                       |
| 所属 Group（英文） | Storage Statistics             |
| Group ID           | `storage_statistics`           |
| 菜单位置           | 库房统计                       |
| 路由路径           | `/storage_statistics`          |
| 页面目录           | `src/pages/storage_statistics` |

## 1. 模块定位与项目作用

库房统计是综合信息平台中「库房统计」业务域下的功能模块，对应页面目录 `src/pages/storage_statistics`。

在项目中的主要作用：

- 作为「库房统计」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
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

| 字段名           | 中文含义                        | 作用说明                        |
| ---------------- | ------------------------------- | ------------------------------- |
| personName       | 出入人员                        | 模块表单/列表字段，详见页面配置 |
| cardNo           | 人员卡号                        | 模块表单/列表字段，详见页面配置 |
| acsName          | 出入门                          | 模块表单/列表字段，详见页面配置 |
| deviceCode       | 门编号                          | 模块表单/列表字段，详见页面配置 |
| passType         | 进出类型                        | 模块表单/列表字段，详见页面配置 |
| passMode         | 通行方式                        | 模块表单/列表字段，详见页面配置 |
| time             | 通行时间                        | 模块表单/列表字段，详见页面配置 |
| enterCount       | storageStatisticsOut            | 模块表单/列表字段，详见页面配置 |
| outCount         | storageStatisticsInStock        | 模块表单/列表字段，详见页面配置 |
| storeName        | storageStatisticsStoreAreaLevel | 模块表单/列表字段，详见页面配置 |
| level            | storageStatisticsMaxCount       | 模块表单/列表字段，详见页面配置 |
| maxCount         | storageStatisticsAlarmCount     | 模块表单/列表字段，详见页面配置 |
| alarmCount       | storageStatisticsRelatedDoor    | 模块表单/列表字段，详见页面配置 |
| militaryPosition | storageStatisticsPassType       | 模块表单/列表字段，详见页面配置 |
| inCount          | storageStatisticsInStock        | 模块表单/列表字段，详见页面配置 |
| deviceNames      | storageStatisticsRelatedDoor    | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

- 导出
- 导入
- 左侧树筛选
- 启用/停用
- 分页查询

---

## 5. 与其他功能模块的关系

### 5.1 相关模块

| 关联模块                  | 文档                                                     | 关系说明             |
| ------------------------- | -------------------------------------------------------- | -------------------- |
| 门禁系统（出入库房/库内） | [door_access_system.md](./door_access_system.md)         | 库房出入相关数据源   |
| 备品备件管理              | [spare_parts_management.md](./spare_parts_management.md) | 备件库存相关         |
| 工具资料                  | [tool_information.md](./tool_information.md)             | 工具/物资库位相关    |
| 统计                      | [statistics.md](./statistics.md)                         | 同属门户统计展示能力 |

### 5.2 上游依赖 / 下游消费

- **上游**：根据本页接口与字段引用，上游主要为：用户及参数管理（`user`）、监控设备（`monitor_equipment`）。另可能依赖登录会话与菜单授权（用户及参数管理）。
- **下游**：门户库房统计展示。

## 6. 关键业务规则与注意事项

1. 操作前确认当前用户具备对应菜单与按钮权限。
2. 删除、导入、批量变更等操作可能影响下游运行态数据，执行前应确认范围。
3. 若模块涉及驱动/采集类配置，变更后可能需要在数采或相关服务侧刷新配置后生效。
4. 接口入参以 Swagger 与前端封装为准，注意必填项与枚举值。
5. 国际化环境下，界面文案以 `src/locales` 配置为准。

---

## 7. 总结

本模块（`storage_statistics`）位于 `src/pages/storage_statistics`，归属「库房统计」。它负责「库房统计」相关业务的页面交互与数据读写。维护本模块时，请同步关注接口契约、字段语义及与兄弟模块的数据一致性。

---

## 8. 接口清单

以下接口由本模块页面代码直接或通过 `@/services` Controller 调用，参数与响应 Schema 来自平台 OpenAPI（若可匹配）。

### 8.1 getCommonFormListByDay

| 项       | 内容                                      |
| -------- | ----------------------------------------- |
| 接口路径 | `/form/getRecordPageByDay`                |
| 请求方法 | `POST`                                    |
| 前端封装 | `SystemController.getCommonFormListByDay` |
| 作用说明 | 见模块业务逻辑                            |

_未在平台 OpenAPI 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---

### 8.2 查询出入库信息统计

| 项          | 内容                                  |
| ----------- | ------------------------------------- |
| 接口路径    | `/store/getStoreInfoStatic`           |
| 请求方法    | `POST`                                |
| 前端封装    | `SystemController.getStoreInfoStatic` |
| Swagger Tag | inventoryApi                          |
| 作用说明    | 查询出入库信息统计                    |

**请求参数（Body）：**

| 字段             | 类型             | 说明 |
| ---------------- | ---------------- | ---- |
| `id`             | `integer`        |      |
| `storeName`      | `string`         |      |
| `deviceCodes`    | `string`         |      |
| `level`          | `string`         |      |
| `remark`         | `string`         |      |
| `maxCount`       | `integer`        |      |
| `alarmCount`     | `integer`        |      |
| `inCount`        | `integer`        |      |
| `startCountTime` | `string`         |      |
| `ids`            | `array<integer>` |      |

**响应体：**

| 字段                  | 类型      | 说明 |
| --------------------- | --------- | ---- |
| `code`                | `integer` |      |
| `message`             | `string`  |      |
| `data`                | `object`  |      |
| `data.id`             | `integer` |      |
| `data.storeName`      | `string`  |      |
| `data.deviceCodes`    | `string`  |      |
| `data.level`          | `string`  |      |
| `data.remark`         | `string`  |      |
| `data.enterCount`     | `integer` |      |
| `data.outCount`       | `integer` |      |
| `data.inCount`        | `integer` |      |
| `data.maxCount`       | `integer` |      |
| `data.alarmCount`     | `integer` |      |
| `data.startCountTime` | `string`  |      |
| `data.createdTime`    | `string`  |      |
| `data.updatedTime`    | `string`  |      |

---

### 8.3 查询库设备出入库人数

| 项          | 内容                              |
| ----------- | --------------------------------- |
| 接口路径    | `/store/getStoreDevice`           |
| 请求方法    | `POST`                            |
| 前端封装    | `SystemController.getStoreDevice` |
| Swagger Tag | inventoryApi                      |
| 作用说明    | 查询库设备出入库人数              |

**请求参数（Body）：**

| 字段             | 类型             | 说明 |
| ---------------- | ---------------- | ---- |
| `id`             | `integer`        |      |
| `storeName`      | `string`         |      |
| `deviceCodes`    | `string`         |      |
| `level`          | `string`         |      |
| `remark`         | `string`         |      |
| `maxCount`       | `integer`        |      |
| `alarmCount`     | `integer`        |      |
| `inCount`        | `integer`        |      |
| `startCountTime` | `string`         |      |
| `ids`            | `array<integer>` |      |

**响应体：**

| 字段                 | 类型            | 说明 |
| -------------------- | --------------- | ---- |
| `code`               | `integer`       |      |
| `message`            | `string`        |      |
| `data`               | `array<object>` |      |
| `data[].id`          | `integer`       |      |
| `data[].deviceCode`  | `string`        |      |
| `data[].enterCount`  | `integer`       |      |
| `data[].outCount`    | `integer`       |      |
| `data[].createdTime` | `string`        |      |
| `data[].updatedTime` | `string`        |      |

---

### 8.4 根据库id获取出入信息

| 项          | 内容                                  |
| ----------- | ------------------------------------- |
| 接口路径    | `/store/getStoreAcsRecords`           |
| 请求方法    | `POST`                                |
| 前端封装    | `SystemController.getStoreAcsRecords` |
| Swagger Tag | inventoryApi                          |
| 作用说明    | 根据库id获取出入信息                  |

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
| `storeName`      | `string`        |      |
| `deviceCode`     | `string`        |      |
| `deviceCodes`    | `string`        |      |
| `id`             | `integer`       |      |

**响应体：**

| 字段                         | 类型            | 说明         |
| ---------------------------- | --------------- | ------------ |
| `code`                       | `integer`       |              |
| `message`                    | `string`        |              |
| `data`                       | `array<object>` |              |
| `data[].id`                  | `integer`       |              |
| `data[].personId`            | `integer`       |              |
| `data[].personName`          | `string`        |              |
| `data[].certificateTypeId`   | `integer`       |              |
| `data[].certificateTypeName` | `string`        |              |
| `data[].certificateNo`       | `string`        |              |
| `data[].dept`                | `string`        |              |
| `data[].cardNo`              | `string`        |              |
| `data[].acsName`             | `string`        |              |
| `data[].time`                | `string`        |              |
| `data[].militaryPosition`    | `string`        |              |
| `data[].passType`            | `integer`       |              |
| `data[].passTypeName`        | `string`        |              |
| `data[].unit`                | `string`        |              |
| `data[].checkPerson`         | `string`        |              |
| `data[].passCount`           | `integer`       |              |
| `data[].sentinelName`        | `string`        |              |
| `data[].itemMethod`          | `string`        |              |
| `data[].passReason`          | `string`        |              |
| `data[].carryProhibitCount`  | `integer`       |              |
| `data[].deviceCode`          | `string`        | 新增设备编码 |
| `data[].deviceGroupId`       | `integer`       | 新增设备分组 |
| `data[].deviceGroupName`     | `string`        |              |
| `data[].passMode`            | `string`        | 新增通行方式 |
| `data[].createdTime`         | `string`        |              |
| `data[].updatedTime`         | `string`        |              |

---

### 8.5 获取内部人员出入库信息列表

| 项          | 内容                                |
| ----------- | ----------------------------------- |
| 接口路径    | `/store/getStoreInfoList`           |
| 请求方法    | `POST`                              |
| 前端封装    | `SystemController.getStoreInfoList` |
| Swagger Tag | inventoryApi                        |
| 作用说明    | 获取内部人员出入库信息列表          |

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
| `storeName`      | `string`        |      |
| `deviceCode`     | `string`        |      |
| `deviceCodes`    | `string`        |      |
| `id`             | `integer`       |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.6 获取门禁设备列表

| 项          | 内容                           |
| ----------- | ------------------------------ |
| 接口路径    | `/device/getDoorList`          |
| 请求方法    | `POST`                         |
| 前端封装    | `SystemController.getDoorList` |
| Swagger Tag | deviceManagementApi            |
| 作用说明    | 获取门禁设备列表               |

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
