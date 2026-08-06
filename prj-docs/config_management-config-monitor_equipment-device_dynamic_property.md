# 设备动态属性（device_dynamic_property）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                                           |
| ------------------ | ------------------------------------------------------------------------------ |
| 模块名称（中文）   | 设备动态属性                                                                   |
| 模块名称（英文）   | Device Dynamic Property                                                        |
| 所属 Group（中文） | 监控设备                                                                       |
| 所属 Group（英文） | Monitor Equipment                                                              |
| Group ID           | `monitor_equipment`                                                            |
| 菜单位置           | 配置管理平台 → 配置管理 → 监控设备 → 设备动态属性                              |
| 路由路径           | `/config_management/config/monitor_equipment/device_dynamic_property`          |
| 页面目录           | `src/pages/config_management/config/monitor_equipment/device_dynamic_property` |

## 1. 模块定位与项目作用

设备动态属性是综合信息平台中「监控设备」业务域下的功能模块，对应页面目录 `src/pages/config_management/config/monitor_equipment/device_dynamic_property`。

在项目中的主要作用：

- 作为「配置管理平台 → 配置管理 → 监控设备 → 设备动态属性」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
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

| 字段名            | 中文含义          | 作用说明                        |
| ----------------- | ----------------- | ------------------------------- |
| remark            | remark            | 模块表单/列表字段，详见页面配置 |
| device            | device            | 模块表单/列表字段，详见页面配置 |
| deviceName        | deviceName        | 模块表单/列表字段，详见页面配置 |
| deviceCode        | deviceCode        | 模块表单/列表字段，详见页面配置 |
| property          | property          | 模块表单/列表字段，详见页面配置 |
| propertyNameZh    | propertyNameZh    | 模块表单/列表字段，详见页面配置 |
| propertyKey       | propertyKey       | 模块表单/列表字段，详见页面配置 |
| propertyNameEn    | propertyNameEn    | 模块表单/列表字段，详见页面配置 |
| isActive          | isActive          | 模块表单/列表字段，详见页面配置 |
| valueType         | valueType         | 模块表单/列表字段，详见页面配置 |
| dataType          | dataType          | 模块表单/列表字段，详见页面配置 |
| propertyValue     | propertyValue     | 模块表单/列表字段，详见页面配置 |
| valueScope        | valueScope        | 模块表单/列表字段，详见页面配置 |
| valueSourceConfig | valueSourceConfig | 模块表单/列表字段，详见页面配置 |
| valueSourceType   | valueSourceType   | 模块表单/列表字段，详见页面配置 |

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

---

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                                    | 关系说明                                     |
| ------------------------------------------- | -------------------------------------------- |
| 设备连接拓扑图（device_connection_diagram） | 同级功能模块，可共同构成「监控设备」业务能力 |
| 设备迁移（device_migrate）                  | 同级功能模块，可共同构成「监控设备」业务能力 |
| 设备管理（equipment_manage）                | 同级功能模块，可共同构成「监控设备」业务能力 |

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

本模块（`device_dynamic_property`）位于 `src/pages/config_management/config/monitor_equipment/device_dynamic_property`，归属「监控设备」。它负责「设备动态属性」相关业务的页面交互与数据读写。维护本模块时，请同步关注接口契约、字段语义及与兄弟模块的数据一致性。

---

## 8. 接口清单

以下接口由本模块页面代码直接或通过 `@/services` Controller 调用，参数与响应 Schema 来自 `swaggerApi.json`（若可匹配）。

### 8.1 获取设备属性列表

| 项          | 内容                                     |
| ----------- | ---------------------------------------- |
| 接口路径    | `/deviceProperty/getDevicePropertyList`  |
| 请求方法    | `POST`                                   |
| 前端封装    | `SystemController.getDevicePropertyList` |
| Swagger Tag | devicePropertyApi                        |
| 作用说明    | 获取设备属性列表                         |

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
| `deviceCode`     | `string`        |      |
| `propertyKey`    | `string`        |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.2 添加设备属性

| 项          | 内容                                 |
| ----------- | ------------------------------------ |
| 接口路径    | `/deviceProperty/addDeviceProperty`  |
| 请求方法    | `POST`                               |
| 前端封装    | `SystemController.addDeviceProperty` |
| Swagger Tag | devicePropertyApi                    |
| 作用说明    | 添加设备属性                         |

**请求参数（Body）：**

| 字段                | 类型             | 说明                           |
| ------------------- | ---------------- | ------------------------------ |
| `id`                | `integer`        |                                |
| `deviceCode`        | `string`         |                                |
| `propertyKey`       | `string`         | 属性键名(程序内部使用)         |
| `propertyNameEn`    | `string`         | 属性英文名称(显示用)           |
| `propertyNameZh`    | `string`         | 属性中文名称(显示用)           |
| `propertyValue`     | `string`         | 属性值                         |
| `valueType`         | `string`         | 值类型                         |
| `dataType`          | `string`         | 数据类型(可选，用于进一步分类) |
| `isActive`          | `integer`        | 是否激活(0:否,1:是)            |
| `valueSourceType`   | `string`         | 数据源配置类型                 |
| `valueSourceConfig` | `string`         | 数据源配置                     |
| `valueScope`        | `string`         | 属性值值范围                   |
| `remark`            | `string`         | 备注                           |
| `ids`               | `array<integer>` |                                |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.3 删除设备属性

| 项          | 内容                                    |
| ----------- | --------------------------------------- |
| 接口路径    | `/deviceProperty/deleteDeviceProperty`  |
| 请求方法    | `POST`                                  |
| 前端封装    | `SystemController.deleteDeviceProperty` |
| Swagger Tag | devicePropertyApi                       |
| 作用说明    | 删除设备属性                            |

**请求参数（Body）：**

| 字段                | 类型             | 说明                           |
| ------------------- | ---------------- | ------------------------------ |
| `id`                | `integer`        |                                |
| `deviceCode`        | `string`         |                                |
| `propertyKey`       | `string`         | 属性键名(程序内部使用)         |
| `propertyNameEn`    | `string`         | 属性英文名称(显示用)           |
| `propertyNameZh`    | `string`         | 属性中文名称(显示用)           |
| `propertyValue`     | `string`         | 属性值                         |
| `valueType`         | `string`         | 值类型                         |
| `dataType`          | `string`         | 数据类型(可选，用于进一步分类) |
| `isActive`          | `integer`        | 是否激活(0:否,1:是)            |
| `valueSourceType`   | `string`         | 数据源配置类型                 |
| `valueSourceConfig` | `string`         | 数据源配置                     |
| `valueScope`        | `string`         | 属性值值范围                   |
| `remark`            | `string`         | 备注                           |
| `ids`               | `array<integer>` |                                |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.4 修改设备属性

| 项          | 内容                                    |
| ----------- | --------------------------------------- |
| 接口路径    | `/deviceProperty/updateDeviceProperty`  |
| 请求方法    | `POST`                                  |
| 前端封装    | `SystemController.updateDeviceProperty` |
| Swagger Tag | devicePropertyApi                       |
| 作用说明    | 修改设备属性                            |

**请求参数（Body）：**

| 字段                | 类型             | 说明                           |
| ------------------- | ---------------- | ------------------------------ |
| `id`                | `integer`        |                                |
| `deviceCode`        | `string`         |                                |
| `propertyKey`       | `string`         | 属性键名(程序内部使用)         |
| `propertyNameEn`    | `string`         | 属性英文名称(显示用)           |
| `propertyNameZh`    | `string`         | 属性中文名称(显示用)           |
| `propertyValue`     | `string`         | 属性值                         |
| `valueType`         | `string`         | 值类型                         |
| `dataType`          | `string`         | 数据类型(可选，用于进一步分类) |
| `isActive`          | `integer`        | 是否激活(0:否,1:是)            |
| `valueSourceType`   | `string`         | 数据源配置类型                 |
| `valueSourceConfig` | `string`         | 数据源配置                     |
| `valueScope`        | `string`         | 属性值值范围                   |
| `remark`            | `string`         | 备注                           |
| `ids`               | `array<integer>` |                                |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.5 获取设备属性详情

| 项          | 内容                                       |
| ----------- | ------------------------------------------ |
| 接口路径    | `/deviceProperty/getDevicePropertyDetail`  |
| 请求方法    | `POST`                                     |
| 前端封装    | `SystemController.getDevicePropertyDetail` |
| Swagger Tag | devicePropertyApi                          |
| 作用说明    | 获取设备属性详情                           |

**请求参数（Body）：**

| 字段                | 类型             | 说明                           |
| ------------------- | ---------------- | ------------------------------ |
| `id`                | `integer`        |                                |
| `deviceCode`        | `string`         |                                |
| `propertyKey`       | `string`         | 属性键名(程序内部使用)         |
| `propertyNameEn`    | `string`         | 属性英文名称(显示用)           |
| `propertyNameZh`    | `string`         | 属性中文名称(显示用)           |
| `propertyValue`     | `string`         | 属性值                         |
| `valueType`         | `string`         | 值类型                         |
| `dataType`          | `string`         | 数据类型(可选，用于进一步分类) |
| `isActive`          | `integer`        | 是否激活(0:否,1:是)            |
| `valueSourceType`   | `string`         | 数据源配置类型                 |
| `valueSourceConfig` | `string`         | 数据源配置                     |
| `valueScope`        | `string`         | 属性值值范围                   |
| `remark`            | `string`         | 备注                           |
| `ids`               | `array<integer>` |                                |

**响应体：**

| 字段                     | 类型      | 说明 |
| ------------------------ | --------- | ---- |
| `code`                   | `integer` |      |
| `message`                | `string`  |      |
| `data`                   | `object`  |      |
| `data.id`                | `integer` |      |
| `data.deviceCode`        | `string`  |      |
| `data.deviceName`        | `string`  |      |
| `data.propertyKey`       | `string`  |      |
| `data.propertyNameEn`    | `string`  |      |
| `data.propertyNameZh`    | `string`  |      |
| `data.propertyValue`     | `string`  |      |
| `data.valueType`         | `string`  |      |
| `data.dataType`          | `string`  |      |
| `data.isActive`          | `integer` |      |
| `data.valueSourceType`   | `string`  |      |
| `data.valueSourceConfig` | `string`  |      |
| `data.valueScope`        | `string`  |      |
| `data.createdBy`         | `string`  |      |
| `data.updatedBy`         | `string`  |      |
| `data.remark`            | `string`  |      |

---

### 8.6 获取设备列表

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

### 8.7 获取设备属性枚举

| 项          | 内容                                     |
| ----------- | ---------------------------------------- |
| 接口路径    | `/deviceProperty/getDevicePropertyEnum`  |
| 请求方法    | `GET`                                    |
| 前端封装    | `SystemController.getDevicePropertyEnum` |
| Swagger Tag | devicePropertyApi                        |
| 作用说明    | 获取设备属性枚举                         |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段           | 类型            | 说明 |
| -------------- | --------------- | ---- |
| `code`         | `integer`       |      |
| `message`      | `string`        |      |
| `data`         | `array<object>` |      |
| `data[].label` | `string`        |      |
| `data[].value` | `string`        |      |

---
