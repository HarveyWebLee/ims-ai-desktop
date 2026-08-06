# 使用（usage）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                                            |
| ------------------ | ------------------------------------------------------------------------------- |
| 模块名称（中文）   | 使用                                                                            |
| 模块名称（英文）   | Usage                                                                           |
| 所属 Group（中文） | 设施管理                                                                        |
| 所属 Group（英文） | Facilities Management                                                           |
| Group ID           | `facilities_management`                                                         |
| 菜单位置           | 配置管理平台 → 阵地管理 → 设施管理 → 使用                                       |
| 路由路径           | `/config_management/positional_management/facilities_management/usage`          |
| 页面目录           | `src/pages/config_management/positional_management/facilities_management/usage` |

## 1. 模块定位与项目作用

使用是综合信息平台中「设施管理」业务域下的功能模块，对应页面目录 `src/pages/config_management/positional_management/facilities_management/usage`。

在项目中的主要作用：

- 作为「配置管理平台 → 阵地管理 → 设施管理 → 使用」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
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

| 字段名             | 中文含义                    | 作用说明                        |
| ------------------ | --------------------------- | ------------------------------- |
| runDevVarName      | 运行设备变量编码            | 模块表单/列表字段，详见页面配置 |
| runDevVarCode      | 设施设备编码                | 模块表单/列表字段，详见页面配置 |
| ctrlDevVarName     | 控制设备变量编码            | 模块表单/列表字段，详见页面配置 |
| ctrlDevVarCode     | 上次保养时间                | 模块表单/列表字段，详见页面配置 |
| runDeviceVar       | 运行设备及变量              | 模块表单/列表字段，详见页面配置 |
| ctrlDeviceVar      | 控制设备及变量              | 模块表单/列表字段，详见页面配置 |
| modelConfig        | 模式配置                    | 模块表单/列表字段，详见页面配置 |
| deviceCategoryId   | 设备类别                    | 模块表单/列表字段，详见页面配置 |
| runDevName         | 运行设备名称                | 模块表单/列表字段，详见页面配置 |
| runDevCode         | 运行设备编码                | 模块表单/列表字段，详见页面配置 |
| facilityDeviceCode | 设施设备编码                | 模块表单/列表字段，详见页面配置 |
| totalTime          | 累计运行时间                | 模块表单/列表字段，详见页面配置 |
| ctrlDevName        | 控制设备名称                | 模块表单/列表字段，详见页面配置 |
| ctrlDevCode        | 控制设备编码                | 模块表单/列表字段，详见页面配置 |
| lastUpkeepTime     | 上次保养时间                | 模块表单/列表字段，详见页面配置 |
| runTime            | 自上次保养运行时间          | 模块表单/列表字段，详见页面配置 |
| status             | 启用状态                    | 模块表单/列表字段，详见页面配置 |
| modelName          | usageManagement.deviceName  | 模块表单/列表字段，详见页面配置 |
| dcn                | usageManagement.deviceCode  | 模块表单/列表字段，详见页面配置 |
| dn                 | usageManagement.varName     | 模块表单/列表字段，详见页面配置 |
| vcn                | usageManagement.varCode     | 模块表单/列表字段，详见页面配置 |
| vn                 | usageManagement.varValue    | 模块表单/列表字段，详见页面配置 |
| vv                 | usageManagement.runDuration | 模块表单/列表字段，详见页面配置 |
| useTime            | usageManagement.runDuration | 模块表单/列表字段，详见页面配置 |
| JSON导入           | JSON导入                    | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

- 新建/新增
- 编辑
- 删除
- 详情回填
- 导出
- 导入
- 复制
- 左侧树筛选
- 启用/停用
- 分页查询

---

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                                    | 关系说明                                     |
| ------------------------------------------- | -------------------------------------------- |
| 属性字典（attribute_dictionary）            | 同级功能模块，可共同构成「设施管理」业务能力 |
| 分类管理（category_management）             | 同级功能模块，可共同构成「设施管理」业务能力 |
| 设施管理（facility_management）             | 同级功能模块，可共同构成「设施管理」业务能力 |
| 交接管理（handover_management）             | 同级功能模块，可共同构成「设施管理」业务能力 |
| 安装位置管理（install_position_management） | 同级功能模块，可共同构成「设施管理」业务能力 |
| 质量统计（quality_statistics）              | 同级功能模块，可共同构成「设施管理」业务能力 |

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

本模块（`usage`）位于 `src/pages/config_management/positional_management/facilities_management/usage`，归属「设施管理」。它负责「使用」相关业务的页面交互与数据读写。维护本模块时，请同步关注接口契约、字段语义及与兄弟模块的数据一致性。

---

## 8. 接口清单

以下接口由本模块页面代码直接或通过 `@/services` Controller 调用，参数与响应 Schema 来自 `swaggerApi.json`（若可匹配）。

### 8.1 获取设备运行统计

| 项          | 内容                              |
| ----------- | --------------------------------- |
| 接口路径    | `/deviceUse/importJsonData`       |
| 请求方法    | `POST`                            |
| 前端封装    | `SystemController.importJsonData` |
| Swagger Tag | deviceUsageApi                    |
| 作用说明    | 获取设备运行统计                  |

**请求参数（Body）：**

| 字段                  | 类型            | 说明 |
| --------------------- | --------------- | ---- |
| `deviceUseJson`       | `array<object>` |      |
| `deviceUseJson[].dns` | `array<string>` |      |
| `deviceUseJson[].vn`  | `string`        |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.2 获取设备动用配置列表

| 项          | 内容                                      |
| ----------- | ----------------------------------------- |
| 接口路径    | `/deviceUse/getDeviceUseConfigList`       |
| 请求方法    | `POST`                                    |
| 前端封装    | `SystemController.getDeviceUseConfigList` |
| Swagger Tag | deviceUsageApi                            |
| 作用说明    | 获取设备动用配置列表                      |

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

### 8.3 获取设备动用信息

| 项          | 内容                                  |
| ----------- | ------------------------------------- |
| 接口路径    | `/deviceUse/addDeviceUseConfig`       |
| 请求方法    | `POST`                                |
| 前端封装    | `SystemController.addDeviceUseConfig` |
| Swagger Tag | deviceUsageApi                        |
| 作用说明    | 获取设备动用信息                      |

**请求参数（Body）：**

| 字段                 | 类型             | 说明 |
| -------------------- | ---------------- | ---- |
| `id`                 | `integer`        |      |
| `facilityDeviceCode` | `string`         |      |
| `ctrlDevName`        | `string`         |      |
| `ctrlDevCode`        | `string`         |      |
| `ctrlDevVarName`     | `string`         |      |
| `ctrlDevVarCode`     | `string`         |      |
| `runDevName`         | `string`         |      |
| `runDevCode`         | `string`         |      |
| `runDevVarName`      | `string`         |      |
| `runDevVarCode`      | `string`         |      |
| `status`             | `integer`        |      |
| `lastUpkeepTime`     | `string`         |      |
| `modelConfig`        | `string`         |      |
| `ids`                | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.4 修改设备动用信息

| 项          | 内容                                   |
| ----------- | -------------------------------------- |
| 接口路径    | `/deviceUse/editDeviceUseConfig`       |
| 请求方法    | `POST`                                 |
| 前端封装    | `SystemController.editDeviceUseConfig` |
| Swagger Tag | deviceUsageApi                         |
| 作用说明    | 修改设备动用信息                       |

**请求参数（Body）：**

| 字段                 | 类型             | 说明 |
| -------------------- | ---------------- | ---- |
| `id`                 | `integer`        |      |
| `facilityDeviceCode` | `string`         |      |
| `ctrlDevName`        | `string`         |      |
| `ctrlDevCode`        | `string`         |      |
| `ctrlDevVarName`     | `string`         |      |
| `ctrlDevVarCode`     | `string`         |      |
| `runDevName`         | `string`         |      |
| `runDevCode`         | `string`         |      |
| `runDevVarName`      | `string`         |      |
| `runDevVarCode`      | `string`         |      |
| `status`             | `integer`        |      |
| `lastUpkeepTime`     | `string`         |      |
| `modelConfig`        | `string`         |      |
| `ids`                | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.5 删除设备动用信息

| 项          | 内容                                  |
| ----------- | ------------------------------------- |
| 接口路径    | `/deviceUse/delDeviceUseConfig`       |
| 请求方法    | `POST`                                |
| 前端封装    | `SystemController.delDeviceUseConfig` |
| Swagger Tag | deviceUsageApi                        |
| 作用说明    | 删除设备动用信息                      |

**请求参数（Body）：**

| 字段                 | 类型             | 说明 |
| -------------------- | ---------------- | ---- |
| `id`                 | `integer`        |      |
| `facilityDeviceCode` | `string`         |      |
| `ctrlDevName`        | `string`         |      |
| `ctrlDevCode`        | `string`         |      |
| `ctrlDevVarName`     | `string`         |      |
| `ctrlDevVarCode`     | `string`         |      |
| `runDevName`         | `string`         |      |
| `runDevCode`         | `string`         |      |
| `runDevVarName`      | `string`         |      |
| `runDevVarCode`      | `string`         |      |
| `status`             | `integer`        |      |
| `lastUpkeepTime`     | `string`         |      |
| `modelConfig`        | `string`         |      |
| `ids`                | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.6 获取设备动用信息

| 项          | 内容                                  |
| ----------- | ------------------------------------- |
| 接口路径    | `/deviceUse/getDeviceUseConfig`       |
| 请求方法    | `POST`                                |
| 前端封装    | `SystemController.getDeviceUseConfig` |
| Swagger Tag | deviceUsageApi                        |
| 作用说明    | 获取设备动用信息                      |

**请求参数（Body）：**

| 字段                 | 类型             | 说明 |
| -------------------- | ---------------- | ---- |
| `id`                 | `integer`        |      |
| `facilityDeviceCode` | `string`         |      |
| `ctrlDevName`        | `string`         |      |
| `ctrlDevCode`        | `string`         |      |
| `ctrlDevVarName`     | `string`         |      |
| `ctrlDevVarCode`     | `string`         |      |
| `runDevName`         | `string`         |      |
| `runDevCode`         | `string`         |      |
| `runDevVarName`      | `string`         |      |
| `runDevVarCode`      | `string`         |      |
| `status`             | `integer`        |      |
| `lastUpkeepTime`     | `string`         |      |
| `modelConfig`        | `string`         |      |
| `ids`                | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.7 导出设备动用配置列表

| 项          | 内容                                         |
| ----------- | -------------------------------------------- |
| 接口路径    | `/deviceUse/writerDeviceUseConfigList`       |
| 请求方法    | `GET`                                        |
| 前端封装    | `SystemController.writerDeviceUseConfigList` |
| Swagger Tag | deviceUsageApi                               |
| 作用说明    | 导出设备动用配置列表                         |

**Query/Path 参数：**

| 参数名               | 位置  | 必填 | 类型     | 说明 |
| -------------------- | ----- | ---- | -------- | ---- |
| `ctrlDevName`        | query | 否   | `string` |      |
| `ctrlDevCode`        | query | 否   | `string` |      |
| `ctrlDevVarName`     | query | 否   | `string` |      |
| `ctrlDevVarCode`     | query | 否   | `string` |      |
| `runDevName`         | query | 否   | `string` |      |
| `runDevCode`         | query | 否   | `string` |      |
| `runDevVarName`      | query | 否   | `string` |      |
| `runDevVarCode`      | query | 否   | `string` |      |
| `status`             | query | 否   | `string` |      |
| `devName`            | query | 否   | `string` |      |
| `devCode`            | query | 否   | `string` |      |
| `startTime`          | query | 否   | `string` |      |
| `startModel`         | query | 否   | `string` |      |
| `startPerson`        | query | 否   | `string` |      |
| `endTime`            | query | 否   | `string` |      |
| `endModel`           | query | 否   | `string` |      |
| `endPerson`          | query | 否   | `string` |      |
| `useTime`            | query | 否   | `string` |      |
| `matchDevCode`       | query | 否   | `string` |      |
| `facilityDeviceCode` | query | 否   | `string` |      |
| `page`               | query | 是   | `string` |      |
| `size`               | query | 是   | `string` |      |
| `search`             | query | 否   | `string` |      |
| `fieldList[0]`       | query | 否   | `string` |      |
| `sorter[0].order`    | query | 否   | `string` |      |
| `sorter[0].field`    | query | 否   | `string` |      |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

---

### 8.8 导入设备动用配置列表

| 项          | 内容                                         |
| ----------- | -------------------------------------------- |
| 接口路径    | `/deviceUse/importDeviceUseConfigList`       |
| 请求方法    | `POST`                                       |
| 前端封装    | `SystemController.importDeviceUseConfigList` |
| Swagger Tag | deviceUsageApi                               |
| 作用说明    | 导入设备动用配置列表                         |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.9 获取设备动用记录列表

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

### 8.10 导出设备动用记录列表

| 项          | 内容                                     |
| ----------- | ---------------------------------------- |
| 接口路径    | `/deviceUse/writerDeviceUseRecordList`   |
| 请求方法    | `GET`                                    |
| 前端封装    | `SystemController.exportDeviceUseRecord` |
| Swagger Tag | deviceUsageApi                           |
| 作用说明    | 导出设备动用记录列表                     |

**Query/Path 参数：**

| 参数名               | 位置  | 必填 | 类型     | 说明 |
| -------------------- | ----- | ---- | -------- | ---- |
| `ctrlDevName`        | query | 否   | `string` |      |
| `ctrlDevCode`        | query | 否   | `string` |      |
| `ctrlDevVarName`     | query | 否   | `string` |      |
| `ctrlDevVarCode`     | query | 否   | `string` |      |
| `runDevName`         | query | 否   | `string` |      |
| `runDevCode`         | query | 否   | `string` |      |
| `runDevVarName`      | query | 否   | `string` |      |
| `runDevVarCode`      | query | 否   | `string` |      |
| `status`             | query | 否   | `string` |      |
| `devName`            | query | 否   | `string` |      |
| `devCode`            | query | 否   | `string` |      |
| `startTime`          | query | 否   | `string` |      |
| `startModel`         | query | 否   | `string` |      |
| `startPerson`        | query | 否   | `string` |      |
| `endTime`            | query | 否   | `string` |      |
| `endModel`           | query | 否   | `string` |      |
| `endPerson`          | query | 否   | `string` |      |
| `useTime`            | query | 否   | `string` |      |
| `matchDevCode`       | query | 否   | `string` |      |
| `facilityDeviceCode` | query | 否   | `string` |      |
| `page`               | query | 是   | `string` |      |
| `size`               | query | 是   | `string` |      |
| `search`             | query | 否   | `string` |      |
| `fieldList[0]`       | query | 否   | `string` |      |
| `sorter[0].order`    | query | 否   | `string` |      |
| `sorter[0].field`    | query | 否   | `string` |      |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

---

### 8.11 删除设备动用记录

| 项          | 内容                                  |
| ----------- | ------------------------------------- |
| 接口路径    | `/deviceUse/delDeviceUseRecord`       |
| 请求方法    | `POST`                                |
| 前端封装    | `SystemController.delDeviceUseRecord` |
| Swagger Tag | deviceUsageApi                        |
| 作用说明    | 删除设备动用记录                      |

**请求参数（Body）：**

| 字段                 | 类型             | 说明 |
| -------------------- | ---------------- | ---- |
| `id`                 | `integer`        |      |
| `devName`            | `string`         |      |
| `devCode`            | `string`         |      |
| `startTime`          | `string`         |      |
| `startModel`         | `string`         |      |
| `startPerson`        | `string`         |      |
| `endTime`            | `string`         |      |
| `endModel`           | `string`         |      |
| `endPerson`          | `string`         |      |
| `modelName`          | `string`         |      |
| `facilityDeviceCode` | `string`         |      |
| `ids`                | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.12 获取设备动用记录

| 项          | 内容                                  |
| ----------- | ------------------------------------- |
| 接口路径    | `/deviceUse/getDeviceUseRecord`       |
| 请求方法    | `POST`                                |
| 前端封装    | `SystemController.getDeviceUseRecord` |
| Swagger Tag | deviceUsageApi                        |
| 作用说明    | 获取设备动用记录                      |

**请求参数（Body）：**

| 字段                 | 类型             | 说明 |
| -------------------- | ---------------- | ---- |
| `id`                 | `integer`        |      |
| `devName`            | `string`         |      |
| `devCode`            | `string`         |      |
| `startTime`          | `string`         |      |
| `startModel`         | `string`         |      |
| `startPerson`        | `string`         |      |
| `endTime`            | `string`         |      |
| `endModel`           | `string`         |      |
| `endPerson`          | `string`         |      |
| `modelName`          | `string`         |      |
| `facilityDeviceCode` | `string`         |      |
| `ids`                | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.13 修改设备动用记录

| 项          | 内容                                   |
| ----------- | -------------------------------------- |
| 接口路径    | `/deviceUse/editDeviceUseRecord`       |
| 请求方法    | `POST`                                 |
| 前端封装    | `SystemController.editDeviceUseRecord` |
| Swagger Tag | deviceUsageApi                         |
| 作用说明    | 修改设备动用记录                       |

**请求参数（Body）：**

| 字段                 | 类型             | 说明 |
| -------------------- | ---------------- | ---- |
| `id`                 | `integer`        |      |
| `devName`            | `string`         |      |
| `devCode`            | `string`         |      |
| `startTime`          | `string`         |      |
| `startModel`         | `string`         |      |
| `startPerson`        | `string`         |      |
| `endTime`            | `string`         |      |
| `endModel`           | `string`         |      |
| `endPerson`          | `string`         |      |
| `modelName`          | `string`         |      |
| `facilityDeviceCode` | `string`         |      |
| `ids`                | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.14 添加设备动用记录

| 项          | 内容                                  |
| ----------- | ------------------------------------- |
| 接口路径    | `/deviceUse/addDeviceUseRecord`       |
| 请求方法    | `POST`                                |
| 前端封装    | `SystemController.addDeviceUseRecord` |
| Swagger Tag | deviceUsageApi                        |
| 作用说明    | 添加设备动用记录                      |

**请求参数（Body）：**

| 字段                 | 类型             | 说明 |
| -------------------- | ---------------- | ---- |
| `id`                 | `integer`        |      |
| `devName`            | `string`         |      |
| `devCode`            | `string`         |      |
| `startTime`          | `string`         |      |
| `startModel`         | `string`         |      |
| `startPerson`        | `string`         |      |
| `endTime`            | `string`         |      |
| `endModel`           | `string`         |      |
| `endPerson`          | `string`         |      |
| `modelName`          | `string`         |      |
| `facilityDeviceCode` | `string`         |      |
| `ids`                | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.15 获取设备运行统计

| 项          | 内容                                 |
| ----------- | ------------------------------------ |
| 接口路径    | `/deviceUse/getDeviceUseCount`       |
| 请求方法    | `POST`                               |
| 前端封装    | `SystemController.getDeviceUseCount` |
| Swagger Tag | deviceUsageApi                       |
| 作用说明    | 获取设备运行统计                     |

**请求参数（Body）：**

| 字段                 | 类型             | 说明 |
| -------------------- | ---------------- | ---- |
| `id`                 | `integer`        |      |
| `facilityDeviceCode` | `string`         |      |
| `ctrlDevName`        | `string`         |      |
| `ctrlDevCode`        | `string`         |      |
| `ctrlDevVarName`     | `string`         |      |
| `ctrlDevVarCode`     | `string`         |      |
| `runDevName`         | `string`         |      |
| `runDevCode`         | `string`         |      |
| `runDevVarName`      | `string`         |      |
| `runDevVarCode`      | `string`         |      |
| `status`             | `integer`        |      |
| `lastUpkeepTime`     | `string`         |      |
| `modelConfig`        | `string`         |      |
| `ids`                | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.16 获取设施设备分类列表

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

### 8.17 获取设施设备列表

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
