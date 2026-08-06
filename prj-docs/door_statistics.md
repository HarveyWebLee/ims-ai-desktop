# 门禁统计（door_statistics）知识库

## 0. 路由与归属信息

| 项                 | 内容                        |
| ------------------ | --------------------------- |
| 模块名称（中文）   | 门禁统计                    |
| 模块名称（英文）   | Door Statistics             |
| 所属 Group（中文） | 门禁统计                    |
| 所属 Group（英文） | Door Statistics             |
| Group ID           | `door_statistics`           |
| 菜单位置           | 门禁统计                    |
| 路由路径           | `/door_statistics`          |
| 页面目录           | `src/pages/door_statistics` |

## 1. 模块定位与项目作用

门禁统计是综合信息平台中「门禁统计」业务域下的功能模块，对应页面目录 `src/pages/door_statistics`。

在项目中的主要作用：

- 作为「门禁统计」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
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

| 字段名           | 中文含义                          | 作用说明                        |
| ---------------- | --------------------------------- | ------------------------------- |
| enterCount       | storageStatisticsOut              | 模块表单/列表字段，详见页面配置 |
| outCount         | storageStatisticsInStock          | 模块表单/列表字段，详见页面配置 |
| applyUnit        | doorStatisticsTeamLeader          | 模块表单/列表字段，详见页面配置 |
| teamLeaderName   | storageStatisticsMilitaryPosition | 模块表单/列表字段，详见页面配置 |
| position         | doorStatisticsActiveArea          | 模块表单/列表字段，详见页面配置 |
| activeArea       | doorStatisticsInTime              | 模块表单/列表字段，详见页面配置 |
| inTime           | doorStatisticsInCount             | 模块表单/列表字段，详见页面配置 |
| inCount          | doorStatisticsInReason            | 模块表单/列表字段，详见页面配置 |
| inReason         | doorStatisticsOutTime             | 模块表单/列表字段，详见页面配置 |
| outTime          | order                             | 模块表单/列表字段，详见页面配置 |
| name             | operation                         | 模块表单/列表字段，详见页面配置 |
| personName       | storageStatisticsCardNo           | 模块表单/列表字段，详见页面配置 |
| cardNo           | unit                              | 模块表单/列表字段，详见页面配置 |
| unitName         | storageStatisticsMilitaryPosition | 模块表单/列表字段，详见页面配置 |
| militaryPosition | storageStatisticsTime             | 模块表单/列表字段，详见页面配置 |
| time             | storageStatisticsTime             | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

- 导出
- 导入
- 左侧树筛选

---

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                                 | 关系说明                                     |
| ---------------------------------------- | -------------------------------------------- |
| 404 页面（404）                          | 同级功能模块，可共同构成「门禁统计」业务能力 |
| GoBinding（go_binding）                  | 同级功能模块，可共同构成「门禁统计」业务能力 |
| 跳转维护（go_to_maintenance）            | 同级功能模块，可共同构成「门禁统计」业务能力 |
| HMI WebSocket 测试（hmi_websocket_test） | 同级功能模块，可共同构成「门禁统计」业务能力 |
| 二级组件（level_2_comp）                 | 同级功能模块，可共同构成「门禁统计」业务能力 |
| 三级组件（level_3_comp）                 | 同级功能模块，可共同构成「门禁统计」业务能力 |
| 登录（login）                            | 同级功能模块，可共同构成「门禁统计」业务能力 |
| 总览（overview）                         | 同级功能模块，可共同构成「门禁统计」业务能力 |
| 页面运行（page）                         | 同级功能模块，可共同构成「门禁统计」业务能力 |
| 统计（statistics）                       | 同级功能模块，可共同构成「门禁统计」业务能力 |
| 库房统计（storage_statistics）           | 同级功能模块，可共同构成「门禁统计」业务能力 |
| 测试页（test_page）                      | 同级功能模块，可共同构成「门禁统计」业务能力 |

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

本模块（`door_statistics`）位于 `src/pages/door_statistics`，归属「门禁统计」。它负责「门禁统计」相关业务的页面交互与数据读写。维护本模块时，请同步关注接口契约、字段语义及与兄弟模块的数据一致性。

---

## 8. 接口清单

以下接口由本模块页面代码直接或通过 `@/services` Controller 调用，参数与响应 Schema 来自 `swaggerApi.json`（若可匹配）。

### 8.1 获取出入库统计信息

| 项          | 内容                                    |
| ----------- | --------------------------------------- |
| 接口路径    | `/store/getStorePersonStatic`           |
| 请求方法    | `GET`                                   |
| 前端封装    | `SystemController.getStorePersonStatic` |
| Swagger Tag | inventoryApi                            |
| 作用说明    | 获取出入库统计信息                      |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段              | 类型      | 说明 |
| ----------------- | --------- | ---- |
| `code`            | `integer` |      |
| `message`         | `string`  |      |
| `data`            | `object`  |      |
| `data.enterCount` | `integer` |      |
| `data.outCount`   | `integer` |      |
| `data.inCount`    | `integer` |      |

---

### 8.2 获取门禁人员详情

| 项          | 内容                                |
| ----------- | ----------------------------------- |
| 接口路径    | `/acs/getAcsPersonById`             |
| 请求方法    | `POST`                              |
| 前端封装    | `SystemController.getAcsPersonById` |
| Swagger Tag | accessControlApi                    |
| 作用说明    | 获取门禁人员详情                    |

**请求参数（Body）：**

| 字段                | 类型             | 说明             |
| ------------------- | ---------------- | ---------------- |
| `id`                | `integer`        |                  |
| `personName`        | `string`         |                  |
| `certificateTypeId` | `integer`        |                  |
| `sex`               | `integer`        |                  |
| `age`               | `integer`        |                  |
| `isSentinel`        | `integer`        |                  |
| `unitName`          | `string`         |                  |
| `militaryPosition`  | `string`         |                  |
| `pic`               | `string`         |                  |
| `signature`         | `string`         |                  |
| `isExternal`        | `integer`        |                  |
| `area`              | `string`         |                  |
| `remark`            | `string`         |                  |
| `cardNo`            | `string`         | 新增卡号和手机号 |
| `phone`             | `string`         |                  |
| `ids`               | `array<integer>` |                  |

**响应体：**

| 字段                       | 类型      | 说明             |
| -------------------------- | --------- | ---------------- |
| `code`                     | `integer` |                  |
| `message`                  | `string`  |                  |
| `data`                     | `object`  |                  |
| `data.id`                  | `integer` |                  |
| `data.personName`          | `string`  |                  |
| `data.certificateTypeId`   | `integer` |                  |
| `data.certificateTypeName` | `string`  |                  |
| `data.sex`                 | `integer` |                  |
| `data.age`                 | `integer` |                  |
| `data.isSentinel`          | `integer` |                  |
| `data.unitName`            | `string`  |                  |
| `data.militaryPosition`    | `string`  |                  |
| `data.pic`                 | `string`  |                  |
| `data.signature`           | `string`  |                  |
| `data.isExternal`          | `integer` |                  |
| `data.area`                | `string`  |                  |
| `data.remark`              | `string`  |                  |
| `data.cardNo`              | `string`  |                  |
| `data.phone`               | `string`  | 新增卡号和手机号 |
| `data.createdTime`         | `string`  |                  |
| `data.updatedTime`         | `string`  |                  |

---

### 8.3 出入库信息分页列表

| 项          | 内容                                      |
| ----------- | ----------------------------------------- |
| 接口路径    | `/store/getStorePersonInfoList`           |
| 请求方法    | `POST`                                    |
| 前端封装    | `SystemController.getStorePersonInfoList` |
| Swagger Tag | inventoryApi                              |
| 作用说明    | 出入库信息分页列表                        |

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
| `applyUnit`      | `string`        |      |
| `teamLeader`     | `string`        |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.4 获取门禁设备列表

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

### 8.5 获取门禁人员列表

| 项          | 内容                                |
| ----------- | ----------------------------------- |
| 接口路径    | `/acs/getAcsPersonList`             |
| 请求方法    | `POST`                              |
| 前端封装    | `SystemController.getAcsPersonList` |
| Swagger Tag | accessControlApi                    |
| 作用说明    | 获取门禁人员列表                    |

**请求参数（Body）：**

| 字段         | 类型            | 说明 |
| ------------ | --------------- | ---- |
| `page`       | `integer`       |      |
| `size`       | `integer`       |      |
| `search`     | `string`        |      |
| `fieldList`  | `array<string>` |      |
| `personName` | `string`        |      |
| `cardNo`     | `string`        |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---
