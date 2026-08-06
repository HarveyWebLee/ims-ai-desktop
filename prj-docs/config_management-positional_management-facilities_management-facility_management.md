# 设施管理（facility_management）知识库

> 上级模块索引：[facilities_management.md](./facilities_management.md) · 总索引：[README.md](./README.md) · 页面总表：[TOTAL-MODULE.md](./TOTAL-MODULE.md)

## 0. 路由与归属信息

| 项                 | 内容                                                                                          |
| ------------------ | --------------------------------------------------------------------------------------------- |
| 模块名称（中文）   | 设施管理                                                                                      |
| 模块名称（英文）   | Facility Management                                                                           |
| 所属 Group（中文） | 设施设备管理                                                                                  |
| 所属 Group（英文） | Facilities and Equipment Management                                                           |
| Group ID           | `facilities_management`                                                                       |
| 菜单位置           | 配置管理平台 → 阵地维护管理 → 设施设备管理 → 设施管理                                         |
| 路由路径           | `/config_management/positional_management/facility_management`                                |
| 页面目录           | `src/pages/config_management/positional_management/facilities_management/facility_management` |

## 1. 模块定位与项目作用

设施管理是综合信息平台中「设施设备管理」业务域下的功能模块，对应页面目录 `src/pages/config_management/positional_management/facilities_management/facility_management`。

在项目中的主要作用：

- 作为「配置管理平台 → 阵地维护管理 → 设施管理」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
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
| deviceName        | 设备名称     | 模块表单/列表字段，详见页面配置 |
| deviceCategoryId  | 设备类别     | 模块表单/列表字段，详见页面配置 |
| deviceCode        | 设施设备编码 | 模块表单/列表字段，详见页面配置 |
| manageCode        | 阵管编码     | 模块表单/列表字段，详见页面配置 |
| unitCode          | 隶属单位     | 模块表单/列表字段，详见页面配置 |
| positionCode      | 阵地代号     | 模块表单/列表字段，详见页面配置 |
| installPositionId | 安装部位     | 模块表单/列表字段，详见页面配置 |
| deviceModel       | 型号规格     | 模块表单/列表字段，详见页面配置 |
| deviceCompany     | 生产厂家     | 模块表单/列表字段，详见页面配置 |
| outTime           | 出厂时间     | 模块表单/列表字段，详见页面配置 |
| installTime       | 安装时间     | 模块表单/列表字段，详见页面配置 |
| qualityStatus     | 质量状况     | 模块表单/列表字段，详见页面配置 |
| managePerson      | 责任人       | 模块表单/列表字段，详见页面配置 |
| deviceType        | 设备类型     | 模块表单/列表字段，详见页面配置 |
| devicePic         | 设备图片     | 模块表单/列表字段，详见页面配置 |
| parentDeviceCode  | 父设备编码   | 模块表单/列表字段，详见页面配置 |
| remark            | 备注         | 模块表单/列表字段，详见页面配置 |
| deviceAttributes  | 设备属性     | 模块表单/列表字段，详见页面配置 |
| 10M               | 10M          | 模块表单/列表字段，详见页面配置 |

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

| 关联模块                                    | 关系说明                                         |
| ------------------------------------------- | ------------------------------------------------ |
| 属性字典（attribute_dictionary）            | 同级功能模块，可共同构成「设施设备管理」业务能力 |
| 分类管理（category_management）             | 同级功能模块，可共同构成「设施设备管理」业务能力 |
| 交接管理（handover_management）             | 同级功能模块，可共同构成「设施设备管理」业务能力 |
| 安装位置管理（install_position_management） | 同级功能模块，可共同构成「设施设备管理」业务能力 |
| 质量统计（quality_statistics）              | 同级功能模块，可共同构成「设施设备管理」业务能力 |
| 使用（usage）                               | 同级功能模块，可共同构成「设施设备管理」业务能力 |

### 5.2 上游依赖 / 下游消费

- **上游**：根据本页接口与字段引用，上游主要为：用户及参数管理（`user`）、监控设备（`monitor_equipment`）、基础数据（`basedata`）。另可能依赖登录会话与菜单授权（用户及参数管理）。
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

本模块（`facility_management`）位于 `src/pages/config_management/positional_management/facilities_management/facility_management`，归属「设施设备管理」。它负责「设施管理」相关业务的页面交互与数据读写。维护本模块时，请同步关注接口契约、字段语义及与兄弟模块的数据一致性。

---

## 8. 接口清单

以下接口由本模块页面代码直接或通过 `@/services` Controller 调用，参数与响应 Schema 来自平台 OpenAPI（若可匹配）。

### 8.1 获取保养记录

| 项          | 内容                                                |
| ----------- | --------------------------------------------------- |
| 接口路径    | `/misUpkeepTask/getMisDeviceUpkeepRecordList`       |
| 请求方法    | `POST`                                              |
| 前端封装    | `PositionalManagement.getMisDeviceUpkeepRecordList` |
| Swagger Tag | facilityUpkeepTaskApi                               |
| 作用说明    | 获取保养记录                                        |

**请求参数（Body）：**

| 字段         | 类型     | 说明      |
| ------------ | -------- | --------- |
| `page`       | `number` | 1         |
| `size`       | `number` | 10        |
| `deviceCode` | `string` | bqbm-1-01 |

**响应体：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

---

### 8.2 获取设备动用记录列表

| 项          | 内容                                      |
| ----------- | ----------------------------------------- |
| 接口路径    | `/deviceUse/getDeviceUseRecordList`       |
| 请求方法    | `POST`                                    |
| 前端封装    | `SystemController.getDeviceUseRecordList` |
| Swagger Tag | deviceUsageApi                            |
| 作用说明    | 获取设备动用记录列表                      |

**请求参数（Body）：**

| 字段                 | 类型            | 说明 |
| -------------------- | --------------- | ---- |
| `ctrlDevName`        | `string`        |      |
| `ctrlDevCode`        | `string`        |      |
| `ctrlDevVarName`     | `string`        |      |
| `ctrlDevVarCode`     | `string`        |      |
| `runDevName`         | `string`        |      |
| `runDevCode`         | `string`        |      |
| `runDevVarName`      | `string`        |      |
| `runDevVarCode`      | `string`        |      |
| `status`             | `integer`       |      |
| `devName`            | `string`        |      |
| `devCode`            | `string`        |      |
| `startTime`          | `string`        |      |
| `startModel`         | `string`        |      |
| `startPerson`        | `string`        |      |
| `endTime`            | `string`        |      |
| `endModel`           | `string`        |      |
| `endPerson`          | `string`        |      |
| `useTime`            | `integer`       |      |
| `matchDevCode`       | `string`        |      |
| `facilityDeviceCode` | `string`        |      |
| `page`               | `integer`       |      |
| `size`               | `integer`       |      |
| `search`             | `string`        |      |
| `fieldList`          | `array<string>` |      |
| `sorter`             | `array<object>` |      |
| `sorter[].order`     | `string`        |      |
| `sorter[].field`     | `string`        |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.3 获取设施设备组件列表

| 项          | 内容                                                     |
| ----------- | -------------------------------------------------------- |
| 接口路径    | `/misFacilityDevice/getMisFacilityDeviceComponentList`   |
| 请求方法    | `POST`                                                   |
| 前端封装    | `PositionalManagement.getMisFacilityDeviceComponentList` |
| Swagger Tag | facilityDeviceApi                                        |
| 作用说明    | 获取设施设备组件列表                                     |

**请求参数（Body）：**

| 字段         | 类型     | 说明 |
| ------------ | -------- | ---- |
| `deviceCode` | `string` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.4 获取设施设备分类列表

| 项          | 内容                                              |
| ----------- | ------------------------------------------------- |
| 接口路径    | `/misFacilityCategory/getMisFacilityCategoryTree` |
| 请求方法    | `POST`                                            |
| 前端封装    | `PositionalManagement.getMiFacilityCategoryTree`  |
| Swagger Tag | facilityCategoryApi                               |
| 作用说明    | 获取设施设备分类列表                              |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.5 获取安装部位数组

| 项          | 内容                                           |
| ----------- | ---------------------------------------------- |
| 接口路径    | `/misFacilityPosition/getMisFacilityPositions` |
| 请求方法    | `POST`                                         |
| 前端封装    | `PositionalManagement.getMisFacilityPositions` |
| Swagger Tag | facilityPositionApi                            |
| 作用说明    | 获取安装部位数组                               |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.6 获取阵地人员列表

| 项          | 内容                                         |
| ----------- | -------------------------------------------- |
| 接口路径    | `/positionPerson/getPositionPersonList`      |
| 请求方法    | `POST`                                       |
| 前端封装    | `PositionalManagement.getPositionPersonList` |
| Swagger Tag | positionPersonnelApi                         |
| 作用说明    | 获取阵地人员列表                             |

**请求参数（Body）：**

| 字段           | 类型             | 说明 |
| -------------- | ---------------- | ---- |
| `id`           | `integer`        |      |
| `personName`   | `string`         |      |
| `militaryName` | `string`         |      |
| `profession`   | `string`         |      |
| `major`        | `string`         |      |
| `skillLevel`   | `string`         |      |
| `ids`          | `array<integer>` |      |

**响应体：**

| 字段                  | 类型            | 说明 |
| --------------------- | --------------- | ---- |
| `code`                | `integer`       |      |
| `message`             | `string`        |      |
| `data`                | `array<object>` |      |
| `data[].id`           | `integer`       |      |
| `data[].personName`   | `string`        |      |
| `data[].militaryName` | `string`        |      |
| `data[].profession`   | `string`        |      |
| `data[].major`        | `string`        |      |
| `data[].skillLevel`   | `string`        |      |
| `data[].createdTime`  | `string`        |      |
| `data[].updatedTime`  | `string`        |      |

---

### 8.7 导出设施设备

| 项          | 内容                                    |
| ----------- | --------------------------------------- |
| 接口路径    | `/misFacilityDevice/exportDeviceData`   |
| 请求方法    | `GET`                                   |
| 前端封装    | `PositionalManagement.exportDeviceData` |
| Swagger Tag | facilityDeviceApi                       |
| 作用说明    | 导出设施设备                            |

**Query/Path 参数：**

| 参数名 | 位置  | 必填 | 类型     | 说明 |
| ------ | ----- | ---- | -------- | ---- |
| `id`   | query | 是   | `string` |      |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

---

### 8.8 导入设施设备

| 项          | 内容                                           |
| ----------- | ---------------------------------------------- |
| 接口路径    | `/misFacilityDevice/importDeviceData`          |
| 请求方法    | `POST`                                         |
| 前端封装    | `PositionalManagement.importMisFacilityDevice` |
| Swagger Tag | facilityDeviceApi                              |
| 作用说明    | 导入设施设备                                   |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.9 获取设施设备列表

| 项          | 内容                                            |
| ----------- | ----------------------------------------------- |
| 接口路径    | `/misFacilityDevice/getMisFacilityDeviceList`   |
| 请求方法    | `POST`                                          |
| 前端封装    | `PositionalManagement.getMisFacilityDeviceList` |
| Swagger Tag | facilityDeviceApi                               |
| 作用说明    | 获取设施设备列表                                |

**请求参数（Body）：**

| 字段                | 类型      | 说明 |
| ------------------- | --------- | ---- |
| `page`              | `integer` |      |
| `size`              | `integer` |      |
| `deviceName`        | `string`  |      |
| `manageCode`        | `string`  |      |
| `installPositionId` | `integer` |      |
| `deviceModel`       | `string`  |      |
| `deviceCategoryId`  | `integer` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.10 添加设施设备

| 项          | 内容                                        |
| ----------- | ------------------------------------------- |
| 接口路径    | `/misFacilityDevice/addMisFacilityDevice`   |
| 请求方法    | `POST`                                      |
| 前端封装    | `PositionalManagement.addMisFacilityDevice` |
| Swagger Tag | facilityDeviceApi                           |
| 作用说明    | 添加设施设备                                |

**请求参数（Body）：**

| 字段                                | 类型            | 说明 |
| ----------------------------------- | --------------- | ---- |
| `deviceType`                        | `integer`       |      |
| `deviceCategoryId`                  | `integer`       |      |
| `manageCode`                        | `string`        |      |
| `unitCode`                          | `string`        |      |
| `positionCode`                      | `string`        |      |
| `parentDeviceCode`                  | `string`        |      |
| `deviceName`                        | `string`        |      |
| `deviceCode`                        | `string`        |      |
| `installPositionId`                 | `integer`       |      |
| `deviceModel`                       | `string`        |      |
| `deviceCompany`                     | `string`        |      |
| `outTime`                           | `string`        |      |
| `installTime`                       | `string`        |      |
| `qualityStatus`                     | `integer`       |      |
| `managePerson`                      | `string`        |      |
| `devicePic`                         | `string`        |      |
| `remark`                            | `string`        |      |
| `deviceAttributes`                  | `array<object>` |      |
| `deviceAttributes[].deviceCode`     | `string`        |      |
| `deviceAttributes[].attributeId`    | `integer`       |      |
| `deviceAttributes[].attributeValue` | `string`        |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.11 获取设施设备

| 项          | 内容                                        |
| ----------- | ------------------------------------------- |
| 接口路径    | `/misFacilityDevice/getMisFacilityDevice`   |
| 请求方法    | `POST`                                      |
| 前端封装    | `PositionalManagement.getMisFacilityDevice` |
| Swagger Tag | facilityDeviceApi                           |
| 作用说明    | 获取设施设备                                |

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

### 8.12 修改设施设备

| 项          | 内容                                         |
| ----------- | -------------------------------------------- |
| 接口路径    | `/misFacilityDevice/editMisFacilityDevice`   |
| 请求方法    | `POST`                                       |
| 前端封装    | `PositionalManagement.editMisFacilityDevice` |
| Swagger Tag | facilityDeviceApi                            |
| 作用说明    | 修改设施设备                                 |

**请求参数（Body）：**

| 字段                                | 类型            | 说明 |
| ----------------------------------- | --------------- | ---- |
| `id`                                | `integer`       |      |
| `deviceType`                        | `integer`       |      |
| `deviceCategoryId`                  | `integer`       |      |
| `manageCode`                        | `string`        |      |
| `unitCode`                          | `string`        |      |
| `positionCode`                      | `string`        |      |
| `parentDeviceCode`                  | `string`        |      |
| `deviceName`                        | `string`        |      |
| `deviceCode`                        | `string`        |      |
| `installPositionId`                 | `integer`       |      |
| `deviceModel`                       | `string`        |      |
| `deviceCompany`                     | `string`        |      |
| `outTime`                           | `string`        |      |
| `installTime`                       | `string`        |      |
| `qualityStatus`                     | `integer`       |      |
| `managePerson`                      | `string`        |      |
| `devicePic`                         | `string`        |      |
| `remark`                            | `string`        |      |
| `deviceAttributes`                  | `array<object>` |      |
| `deviceAttributes[].deviceCode`     | `string`        |      |
| `deviceAttributes[].attributeId`    | `integer`       |      |
| `deviceAttributes[].attributeValue` | `string`        |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.13 delBatchMisFacilityDevice

| 项       | 内容                                             |
| -------- | ------------------------------------------------ |
| 接口路径 | `/misFacilityDevice/delBatchMisFacilityDevice`   |
| 请求方法 | `POST`                                           |
| 前端封装 | `PositionalManagement.delBatchMisFacilityDevice` |
| 作用说明 | 见模块业务逻辑                                   |

_未在平台 OpenAPI 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---
