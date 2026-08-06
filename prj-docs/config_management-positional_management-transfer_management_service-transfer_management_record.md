# 调拨管理记录（transfer_management_record）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                                                                       |
| ------------------ | ---------------------------------------------------------------------------------------------------------- |
| 模块名称（中文）   | 调拨管理记录                                                                                               |
| 模块名称（英文）   | Transfer Management Record                                                                                 |
| 所属 Group（中文） | 调拨管理                                                                                                   |
| 所属 Group（英文） | Transfer Management                                                                                        |
| Group ID           | `transfer_management_service`                                                                              |
| 菜单位置           | 配置管理平台 → 阵地管理 → 调拨管理 → 调拨管理记录                                                          |
| 路由路径           | `/config_management/positional_management/transfer_management_service/transfer_management_record`          |
| 页面目录           | `src/pages/config_management/positional_management/transfer_management_service/transfer_management_record` |

## 1. 模块定位与项目作用

调拨管理记录是综合信息平台中「调拨管理」业务域下的功能模块，对应页面目录 `src/pages/config_management/positional_management/transfer_management_service/transfer_management_record`。

在项目中的主要作用：

- 作为「配置管理平台 → 阵地管理 → 调拨管理 → 调拨管理记录」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
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

| 字段名           | 中文含义     | 作用说明                        |
| ---------------- | ------------ | ------------------------------- |
| handoverCode     | 移交单号     | 模块表单/列表字段，详见页面配置 |
| handoverPerson   | 交付人       | 模块表单/列表字段，详见页面配置 |
| acceptPerson     | 接收人       | 模块表单/列表字段，详见页面配置 |
| invigilatePerson | 监交人       | 模块表单/列表字段，详见页面配置 |
| timeRange        | 交接时间范围 | 模块表单/列表字段，详见页面配置 |
| handoverTime     | 交接时间     | 模块表单/列表字段，详见页面配置 |
| handoverPic      | 移交物资附件 | 模块表单/列表字段，详见页面配置 |
| remark           | 备注         | 模块表单/列表字段，详见页面配置 |
| file             | file         | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

- 新建/新增
- 编辑
- 删除
- 详情回填
- 导出
- 导入

---

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

暂无明显同级兄弟模块，或同级目录未识别为独立页面。

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

本模块（`transfer_management_record`）位于 `src/pages/config_management/positional_management/transfer_management_service/transfer_management_record`，归属「调拨管理」。它负责「调拨管理记录」相关业务的页面交互与数据读写。维护本模块时，请同步关注接口契约、字段语义及与兄弟模块的数据一致性。

---

## 8. 接口清单

以下接口由本模块页面代码直接或通过 `@/services` Controller 调用，参数与响应 Schema 来自 `swaggerApi.json`（若可匹配）。

### 8.1 批量删除MisHandoverDevices

| 项          | 内容                                         |
| ----------- | -------------------------------------------- |
| 接口路径    | `/misHandoverDevice/delMisHandoverDevices`   |
| 请求方法    | `POST`                                       |
| 前端封装    | `PositionalManagement.delMisHandoverDevices` |
| Swagger Tag | facilityHandoverDeviceApi                    |
| 作用说明    | 批量删除MisHandoverDevices                   |

**请求参数（Body）：**

| 字段               | 类型             | 说明 |
| ------------------ | ---------------- | ---- |
| `id`               | `integer`        |      |
| `handoverFormId`   | `integer`        |      |
| `deviceIndex`      | `integer`        |      |
| `deviceName`       | `string`         |      |
| `deviceModel`      | `string`         |      |
| `deviceNum`        | `integer`        |      |
| `deviceCode`       | `string`         |      |
| `devicePrice`      | `string`         |      |
| `deviceTotalPrice` | `string`         |      |
| `remark`           | `string`         |      |
| `ids`              | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.2 导出MisHandoverDevice列表

| 项          | 内容                                               |
| ----------- | -------------------------------------------------- |
| 接口路径    | `/misHandoverDevice/exportMisHandoverDeviceList`   |
| 请求方法    | `GET`                                              |
| 前端封装    | `PositionalManagement.exportMisHandoverDeviceList` |
| Swagger Tag | facilityHandoverDeviceApi                          |
| 作用说明    | 导出MisHandoverDevice列表                          |

**Query/Path 参数：**

| 参数名                   | 位置  | 必填 | 类型     | 说明 |
| ------------------------ | ----- | ---- | -------- | ---- |
| `page`                   | query | 是   | `string` |      |
| `size`                   | query | 是   | `string` |      |
| `search`                 | query | 否   | `string` |      |
| `fieldList[0]`           | query | 否   | `string` |      |
| `deviceName`             | query | 否   | `string` |      |
| `deviceType`             | query | 否   | `string` |      |
| `manageCode`             | query | 否   | `string` |      |
| `installPositionId`      | query | 否   | `string` |      |
| `deviceModel`            | query | 否   | `string` |      |
| `deviceCategoryId`       | query | 否   | `string` |      |
| `deviceCode`             | query | 否   | `string` |      |
| `handoverUnit`           | query | 否   | `string` |      |
| `acceptUnit`             | query | 否   | `string` |      |
| `startTime`              | query | 否   | `string` |      |
| `endTime`                | query | 否   | `string` |      |
| `upkeepType`             | query | 否   | `string` |      |
| `sceneName`              | query | 否   | `string` |      |
| `taskStatus`             | query | 否   | `string` |      |
| `taskManager`            | query | 否   | `string` |      |
| `toolTypeId`             | query | 否   | `string` |      |
| `toolTypeName`           | query | 否   | `string` |      |
| `toolName`               | query | 否   | `string` |      |
| `toolModel`              | query | 否   | `string` |      |
| `storagePositionId`      | query | 否   | `string` |      |
| `storagePositionName`    | query | 否   | `string` |      |
| `fileName`               | query | 否   | `string` |      |
| `fileCategoryId`         | query | 否   | `string` |      |
| `sparePartName`          | query | 否   | `string` |      |
| `sparePartSpecification` | query | 否   | `string` |      |
| `sparePartSituation`     | query | 否   | `string` |      |
| `recordType`             | query | 否   | `string` |      |
| `toolId`                 | query | 否   | `string` |      |
| `sparePartId`            | query | 否   | `string` |      |
| `meteringObject`         | query | 否   | `string` |      |
| `meteringCode`           | query | 否   | `string` |      |
| `faultDeviceName`        | query | 否   | `string` |      |
| `ids[0]`                 | query | 否   | `string` |      |
| `exportSize`             | query | 否   | `string` |      |
| `handoverCode`           | query | 否   | `string` |      |
| `handoverPerson`         | query | 否   | `string` |      |
| `acceptPerson`           | query | 否   | `string` |      |
| `invigilatePerson`       | query | 否   | `string` |      |
| `handoverFormId`         | query | 否   | `string` |      |
| `repairObject`           | query | 否   | `string` |      |
| `repairProject`          | query | 否   | `string` |      |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

---

### 8.3 获取MisHandoverDevice列表

| 项          | 内容                                            |
| ----------- | ----------------------------------------------- |
| 接口路径    | `/misHandoverDevice/getMisHandoverDeviceList`   |
| 请求方法    | `POST`                                          |
| 前端封装    | `PositionalManagement.getMisHandoverDeviceList` |
| Swagger Tag | facilityHandoverDeviceApi                       |
| 作用说明    | 获取MisHandoverDevice列表                       |

**请求参数（Body）：**

| 字段                     | 类型             | 说明 |
| ------------------------ | ---------------- | ---- |
| `page`                   | `integer`        |      |
| `size`                   | `integer`        |      |
| `search`                 | `string`         |      |
| `fieldList`              | `array<string>`  |      |
| `deviceName`             | `string`         |      |
| `deviceType`             | `integer`        |      |
| `manageCode`             | `string`         |      |
| `installPositionId`      | `integer`        |      |
| `deviceModel`            | `string`         |      |
| `deviceCategoryId`       | `integer`        |      |
| `deviceCode`             | `string`         |      |
| `handoverUnit`           | `string`         |      |
| `acceptUnit`             | `string`         |      |
| `startTime`              | `string`         |      |
| `endTime`                | `string`         |      |
| `upkeepType`             | `integer`        |      |
| `sceneName`              | `string`         |      |
| `taskStatus`             | `integer`        |      |
| `taskManager`            | `string`         |      |
| `toolTypeId`             | `integer`        |      |
| `toolTypeName`           | `string`         |      |
| `toolName`               | `string`         |      |
| `toolModel`              | `string`         |      |
| `storagePositionId`      | `integer`        |      |
| `storagePositionName`    | `string`         |      |
| `fileName`               | `string`         |      |
| `fileCategoryId`         | `integer`        |      |
| `sparePartName`          | `string`         |      |
| `sparePartSpecification` | `string`         |      |
| `sparePartSituation`     | `string`         |      |
| `recordType`             | `integer`        |      |
| `toolId`                 | `integer`        |      |
| `sparePartId`            | `integer`        |      |
| `meteringObject`         | `string`         |      |
| `meteringCode`           | `string`         |      |
| `faultDeviceName`        | `string`         |      |
| `ids`                    | `array<integer>` |      |
| `exportSize`             | `integer`        |      |
| `handoverCode`           | `string`         |      |
| `handoverPerson`         | `string`         |      |
| `acceptPerson`           | `string`         |      |
| `invigilatePerson`       | `string`         |      |
| `handoverFormId`         | `integer`        |      |
| `repairObject`           | `string`         |      |
| `repairProject`          | `string`         |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.4 导入MisHandoverDevice数据

| 项          | 内容                                               |
| ----------- | -------------------------------------------------- |
| 接口路径    | `/misHandoverDevice/importMisHandoverDeviceList`   |
| 请求方法    | `POST`                                             |
| 前端封装    | `PositionalManagement.importMisHandoverDeviceList` |
| Swagger Tag | facilityHandoverDeviceApi                          |
| 作用说明    | 导入MisHandoverDevice数据                          |

**Query/Path 参数：**

| 参数名           | 位置  | 必填 | 类型     | 说明 |
| ---------------- | ----- | ---- | -------- | ---- |
| `handoverFormId` | query | 否   | `string` |      |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.5 添加MisHandoverDevice

| 项          | 内容                                        |
| ----------- | ------------------------------------------- |
| 接口路径    | `/misHandoverDevice/addMisHandoverDevice`   |
| 请求方法    | `POST`                                      |
| 前端封装    | `PositionalManagement.addMisHandoverDevice` |
| Swagger Tag | facilityHandoverDeviceApi                   |
| 作用说明    | 添加MisHandoverDevice                       |

**请求参数（Body）：**

| 字段               | 类型             | 说明 |
| ------------------ | ---------------- | ---- |
| `id`               | `integer`        |      |
| `handoverFormId`   | `integer`        |      |
| `deviceIndex`      | `integer`        |      |
| `deviceName`       | `string`         |      |
| `deviceModel`      | `string`         |      |
| `deviceNum`        | `integer`        |      |
| `deviceCode`       | `string`         |      |
| `devicePrice`      | `string`         |      |
| `deviceTotalPrice` | `string`         |      |
| `remark`           | `string`         |      |
| `ids`              | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.6 删除MisHandoverDevice

| 项          | 内容                                        |
| ----------- | ------------------------------------------- |
| 接口路径    | `/misHandoverDevice/delMisHandoverDevice`   |
| 请求方法    | `POST`                                      |
| 前端封装    | `PositionalManagement.delMisHandoverDevice` |
| Swagger Tag | facilityHandoverDeviceApi                   |
| 作用说明    | 删除MisHandoverDevice                       |

**请求参数（Body）：**

| 字段               | 类型             | 说明 |
| ------------------ | ---------------- | ---- |
| `id`               | `integer`        |      |
| `handoverFormId`   | `integer`        |      |
| `deviceIndex`      | `integer`        |      |
| `deviceName`       | `string`         |      |
| `deviceModel`      | `string`         |      |
| `deviceNum`        | `integer`        |      |
| `deviceCode`       | `string`         |      |
| `devicePrice`      | `string`         |      |
| `deviceTotalPrice` | `string`         |      |
| `remark`           | `string`         |      |
| `ids`              | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.7 修改MisHandoverDevice

| 项          | 内容                                         |
| ----------- | -------------------------------------------- |
| 接口路径    | `/misHandoverDevice/editMisHandoverDevice`   |
| 请求方法    | `POST`                                       |
| 前端封装    | `PositionalManagement.editMisHandoverDevice` |
| Swagger Tag | facilityHandoverDeviceApi                    |
| 作用说明    | 修改MisHandoverDevice                        |

**请求参数（Body）：**

| 字段               | 类型             | 说明 |
| ------------------ | ---------------- | ---- |
| `id`               | `integer`        |      |
| `handoverFormId`   | `integer`        |      |
| `deviceIndex`      | `integer`        |      |
| `deviceName`       | `string`         |      |
| `deviceModel`      | `string`         |      |
| `deviceNum`        | `integer`        |      |
| `deviceCode`       | `string`         |      |
| `devicePrice`      | `string`         |      |
| `deviceTotalPrice` | `string`         |      |
| `remark`           | `string`         |      |
| `ids`              | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.8 获取MisHandoverForm列表

| 项          | 内容                                          |
| ----------- | --------------------------------------------- |
| 接口路径    | `/misHandoverForm/getMisHandoverFormList`     |
| 请求方法    | `POST`                                        |
| 前端封装    | `PositionalManagement.getMisHandoverFormList` |
| Swagger Tag | facilityHandoverFormApi                       |
| 作用说明    | 获取MisHandoverForm列表                       |

**请求参数（Body）：**

| 字段               | 类型      | 说明 |
| ------------------ | --------- | ---- |
| `page`             | `integer` |      |
| `size`             | `integer` |      |
| `handoverCode`     | `string`  |      |
| `handoverPerson`   | `string`  |      |
| `acceptPerson`     | `string`  |      |
| `invigilatePerson` | `string`  |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.9 添加MisHandoverForm

| 项          | 内容                                      |
| ----------- | ----------------------------------------- |
| 接口路径    | `/misHandoverForm/addMisHandoverForm`     |
| 请求方法    | `POST`                                    |
| 前端封装    | `PositionalManagement.addMisHandoverForm` |
| Swagger Tag | facilityHandoverFormApi                   |
| 作用说明    | 添加MisHandoverForm                       |

**请求参数（Body）：**

| 字段               | 类型     | 说明 |
| ------------------ | -------- | ---- |
| `handoverCode`     | `string` |      |
| `handoverTime`     | `string` |      |
| `handoverPerson`   | `string` |      |
| `acceptPerson`     | `string` |      |
| `invigilatePerson` | `string` |      |
| `handoverPic`      | `string` |      |
| `remark`           | `string` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.10 获取MisHandoverForm

| 项          | 内容                                      |
| ----------- | ----------------------------------------- |
| 接口路径    | `/misHandoverForm/getMisHandoverForm`     |
| 请求方法    | `POST`                                    |
| 前端封装    | `PositionalManagement.getMisHandoverForm` |
| Swagger Tag | facilityHandoverFormApi                   |
| 作用说明    | 获取MisHandoverForm                       |

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

### 8.11 修改MisHandoverForm

| 项          | 内容                                       |
| ----------- | ------------------------------------------ |
| 接口路径    | `/misHandoverForm/editMisHandoverForm`     |
| 请求方法    | `POST`                                     |
| 前端封装    | `PositionalManagement.editMisHandoverForm` |
| Swagger Tag | facilityHandoverFormApi                    |
| 作用说明    | 修改MisHandoverForm                        |

**请求参数（Body）：**

| 字段               | 类型      | 说明 |
| ------------------ | --------- | ---- |
| `id`               | `integer` |      |
| `handoverCode`     | `string`  |      |
| `handoverTime`     | `string`  |      |
| `handoverPerson`   | `string`  |      |
| `acceptPerson`     | `string`  |      |
| `invigilatePerson` | `string`  |      |
| `handoverPic`      | `string`  |      |
| `remark`           | `string`  |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.12 批量删除MisHandoverForms

| 项          | 内容                                       |
| ----------- | ------------------------------------------ |
| 接口路径    | `/misHandoverForm/delMisHandoverForms`     |
| 请求方法    | `POST`                                     |
| 前端封装    | `PositionalManagement.delMisHandoverForms` |
| Swagger Tag | facilityHandoverFormApi                    |
| 作用说明    | 批量删除MisHandoverForms                   |

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
