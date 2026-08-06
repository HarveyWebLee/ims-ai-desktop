# 工具管理（tool_management）知识库

> 上级模块索引：[tool_information.md](./tool_information.md) · 总索引：[README.md](./README.md) · 页面总表：[TOTAL-MODULE.md](./TOTAL-MODULE.md)

## 0. 路由与归属信息

| 项                 | 内容                                                                                 |
| ------------------ | ------------------------------------------------------------------------------------ |
| 模块名称（中文）   | 工具管理                                                                             |
| 模块名称（英文）   | Tool Management                                                                      |
| 所属 Group（中文） | 工具资料                                                                             |
| 所属 Group（英文） | Tools and Materials                                                                  |
| Group ID           | `tool_information`                                                                   |
| 菜单位置           | 配置管理平台 → 阵地维护管理 → 工具资料 → 工具管理                                    |
| 路由路径           | `/config_management/positional_management/tool_management`                           |
| 页面目录           | `src/pages/config_management/positional_management/tool_information/tool_management` |

## 1. 模块定位与项目作用

工具管理是综合信息平台中「工具资料」业务域下的功能模块，对应页面目录 `src/pages/config_management/positional_management/tool_information/tool_management`。

在项目中的主要作用：

- 作为「配置管理平台 → 阵地维护管理 → 工具资料 → 工具管理」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
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

| 字段名            | 中文含义 | 作用说明                        |
| ----------------- | -------- | ------------------------------- |
| toolTypeId        | 工具类型 | 模块表单/列表字段，详见页面配置 |
| toolName          | 名称     | 模块表单/列表字段，详见页面配置 |
| toolModel         | 工具型号 | 模块表单/列表字段，详见页面配置 |
| toolCode          | 工具编号 | 模块表单/列表字段，详见页面配置 |
| matchingTime      | 配套时间 | 模块表单/列表字段，详见页面配置 |
| storagePositionId | 存放位置 | 模块表单/列表字段，详见页面配置 |
| countUnit         | 计数单位 | 模块表单/列表字段，详见页面配置 |
| standardNum       | 标准数量 | 模块表单/列表字段，详见页面配置 |
| actualNum         | 实际数量 | 模块表单/列表字段，详见页面配置 |
| usableNum         | 可用数量 | 模块表单/列表字段，详见页面配置 |
| toolSituation     | 质量状况 | 模块表单/列表字段，详见页面配置 |
| toolManager       | 责任人   | 模块表单/列表字段，详见页面配置 |
| remark            | 备注     | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

- 新建/新增
- 编辑
- 删除
- 详情回填
- 导出
- 导入
- 启用/停用

---

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                                    | 关系说明                                     |
| ------------------------------------------- | -------------------------------------------- |
| 入库存管理（in_stock_management）           | 同级功能模块，可共同构成「工具资料」业务能力 |
| 物资管理（material_management）             | 同级功能模块，可共同构成「工具资料」业务能力 |
| 仓储位置管理（storage_position_management） | 同级功能模块，可共同构成「工具资料」业务能力 |
| 工具类型管理（tool_type_management）        | 同级功能模块，可共同构成「工具资料」业务能力 |

### 5.2 上游依赖 / 下游消费

- **上游**：根据本页接口与字段引用，上游主要为：监控设备（`monitor_equipment`）、备品备件管理（`spare_parts_management`）、用户及参数管理（`user`）。另可能依赖登录会话与菜单授权（用户及参数管理）。
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

本模块（`tool_management`）位于 `src/pages/config_management/positional_management/tool_information/tool_management`，归属「工具资料」。它负责「工具管理」相关业务的页面交互与数据读写。维护本模块时，请同步关注接口契约、字段语义及与兄弟模块的数据一致性。

---

## 8. 接口清单

以下接口由本模块页面代码直接或通过 `@/services` Controller 调用，参数与响应 Schema 来自平台 OpenAPI（若可匹配）。

### 8.1 获取MisToolCount列表

| 项          | 内容                                        |
| ----------- | ------------------------------------------- |
| 接口路径    | `/misToolCount/getMisToolCountList`         |
| 请求方法    | `POST`                                      |
| 前端封装    | `ToolManagementController.getToolCountList` |
| Swagger Tag | facilityToolStatsApi                        |
| 作用说明    | 获取MisToolCount列表                        |

**请求参数（Body）：**

| 字段                     | 类型            | 说明 |
| ------------------------ | --------------- | ---- |
| `page`                   | `integer`       |      |
| `size`                   | `integer`       |      |
| `search`                 | `string`        |      |
| `fieldList`              | `array<string>` |      |
| `deviceName`             | `string`        |      |
| `deviceType`             | `integer`       |      |
| `manageCode`             | `string`        |      |
| `installPositionId`      | `integer`       |      |
| `deviceModel`            | `string`        |      |
| `deviceCategoryId`       | `integer`       |      |
| `deviceCode`             | `string`        |      |
| `handoverUnit`           | `string`        |      |
| `acceptUnit`             | `string`        |      |
| `startTime`              | `string`        |      |
| `endTime`                | `string`        |      |
| `upkeepType`             | `integer`       |      |
| `sceneName`              | `string`        |      |
| `taskStatus`             | `integer`       |      |
| `taskManager`            | `string`        |      |
| `toolTypeId`             | `integer`       |      |
| `toolTypeName`           | `string`        |      |
| `toolName`               | `string`        |      |
| `toolModel`              | `string`        |      |
| `storagePositionId`      | `integer`       |      |
| `storagePositionName`    | `string`        |      |
| `fileName`               | `string`        |      |
| `fileCategoryId`         | `integer`       |      |
| `sparePartName`          | `string`        |      |
| `sparePartSpecification` | `string`        |      |
| `sparePartSituation`     | `string`        |      |
| `recordType`             | `integer`       |      |
| `toolId`                 | `integer`       |      |
| `sparePartId`            | `integer`       |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.2 获取工具管理列表

| 项          | 内容                                   |
| ----------- | -------------------------------------- |
| 接口路径    | `/misTool/getMisToolList`              |
| 请求方法    | `POST`                                 |
| 前端封装    | `ToolManagementController.getToolList` |
| Swagger Tag | facilityToolApi                        |
| 作用说明    | 获取工具管理列表                       |

**请求参数（Body）：**

| 字段         | 类型      | 说明 |
| ------------ | --------- | ---- |
| `page`       | `integer` |      |
| `size`       | `integer` |      |
| `toolTypeId` | `integer` |      |
| `toolName`   | `string`  |      |
| `toolModel`  | `string`  |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.3 添加工具管理

| 项          | 内容                               |
| ----------- | ---------------------------------- |
| 接口路径    | `/misTool/addMisTool`              |
| 请求方法    | `POST`                             |
| 前端封装    | `ToolManagementController.addTool` |
| Swagger Tag | facilityToolApi                    |
| 作用说明    | 添加工具管理                       |

**请求参数（Body）：**

| 字段                | 类型      | 说明 |
| ------------------- | --------- | ---- |
| `toolName`          | `string`  |      |
| `toolCode`          | `string`  |      |
| `toolModel`         | `string`  |      |
| `toolTypeId`        | `integer` |      |
| `matchingTime`      | `string`  |      |
| `storagePositionId` | `integer` |      |
| `countUnit`         | `string`  |      |
| `standardNum`       | `integer` |      |
| `actualNum`         | `integer` |      |
| `usableNum`         | `integer` |      |
| `toolManager`       | `string`  |      |
| `remark`            | `string`  |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.4 获取工具管理详情

| 项          | 内容                               |
| ----------- | ---------------------------------- |
| 接口路径    | `/misTool/getMisTool`              |
| 请求方法    | `POST`                             |
| 前端封装    | `ToolManagementController.getTool` |
| Swagger Tag | facilityToolApi                    |
| 作用说明    | 获取工具管理详情                   |

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

### 8.5 修改工具管理

| 项          | 内容                                  |
| ----------- | ------------------------------------- |
| 接口路径    | `/misTool/editMisTool`                |
| 请求方法    | `POST`                                |
| 前端封装    | `ToolManagementController.updateTool` |
| Swagger Tag | facilityToolApi                       |
| 作用说明    | 修改工具管理                          |

**请求参数（Body）：**

| 字段                | 类型      | 说明 |
| ------------------- | --------- | ---- |
| `id`                | `integer` |      |
| `toolName`          | `string`  |      |
| `toolCode`          | `string`  |      |
| `toolModel`         | `string`  |      |
| `toolTypeId`        | `integer` |      |
| `matchingTime`      | `string`  |      |
| `storagePositionId` | `integer` |      |
| `countUnit`         | `string`  |      |
| `standardNum`       | `integer` |      |
| `actualNum`         | `integer` |      |
| `usableNum`         | `integer` |      |
| `toolManager`       | `string`  |      |
| `remark`            | `string`  |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.6 批量删除工具管理

| 项          | 内容                                  |
| ----------- | ------------------------------------- |
| 接口路径    | `/misTool/delMisTools`                |
| 请求方法    | `POST`                                |
| 前端封装    | `ToolManagementController.deleteTool` |
| Swagger Tag | facilityToolApi                       |
| 作用说明    | 批量删除工具管理                      |

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

### 8.7 添加MisToolCount

| 项          | 内容                                    |
| ----------- | --------------------------------------- |
| 接口路径    | `/misToolCount/addMisToolCount`         |
| 请求方法    | `POST`                                  |
| 前端封装    | `ToolManagementController.addToolCount` |
| Swagger Tag | facilityToolStatsApi                    |
| 作用说明    | 添加MisToolCount                        |

**请求参数（Body）：**

| 字段           | 类型             | 说明 |
| -------------- | ---------------- | ---- |
| `id`           | `integer`        |      |
| `toolId`       | `integer`        |      |
| `recordNum`    | `integer`        |      |
| `recordType`   | `integer`        |      |
| `recordPerson` | `string`         |      |
| `remark`       | `string`         |      |
| `ids`          | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.8 删除MisToolCount

| 项          | 内容                                       |
| ----------- | ------------------------------------------ |
| 接口路径    | `/misToolCount/delMisToolCount`            |
| 请求方法    | `POST`                                     |
| 前端封装    | `ToolManagementController.deleteToolCount` |
| Swagger Tag | facilityToolStatsApi                       |
| 作用说明    | 删除MisToolCount                           |

**请求参数（Body）：**

| 字段           | 类型             | 说明 |
| -------------- | ---------------- | ---- |
| `id`           | `integer`        |      |
| `toolId`       | `integer`        |      |
| `recordNum`    | `integer`        |      |
| `recordType`   | `integer`        |      |
| `recordPerson` | `string`         |      |
| `remark`       | `string`         |      |
| `ids`          | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.9 获取工具类型数组

| 项          | 内容                                           |
| ----------- | ---------------------------------------------- |
| 接口路径    | `/misToolType/getMisToolTypeArray`             |
| 请求方法    | `POST`                                         |
| 前端封装    | `ToolManagementController.getMisToolTypeArray` |
| Swagger Tag | facilityToolTypeApi                            |
| 作用说明    | 获取工具类型数组                               |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.10 获取存放位置数组

| 项          | 内容                                                  |
| ----------- | ----------------------------------------------------- |
| 接口路径    | `/misStoragePosition/getMisStoragePositionArray`      |
| 请求方法    | `POST`                                                |
| 前端封装    | `ToolManagementController.getMisStoragePositionArray` |
| Swagger Tag | facilityStoragePositionApi                            |
| 作用说明    | 获取存放位置数组                                      |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.11 获取设施设备分类列表

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

### 8.12 获取安装部位数组

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

### 8.13 获取阵地人员列表

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
