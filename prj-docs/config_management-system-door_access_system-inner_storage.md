# 内部仓储（inner_storage）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                                  |
| ------------------ | --------------------------------------------------------------------- |
| 模块名称（中文）   | 内部仓储                                                              |
| 模块名称（英文）   | Inner Storage                                                         |
| 所属 Group（中文） | 门禁系统                                                              |
| 所属 Group（英文） | Door Access System                                                    |
| Group ID           | `door_access_system`                                                  |
| 菜单位置           | 配置管理平台 → 系统管理 → 门禁系统 → 内部仓储                         |
| 路由路径           | `/config_management/system/door_access_system/inner_storage`          |
| 页面目录           | `src/pages/config_management/system/door_access_system/inner_storage` |

## 1. 模块定位与项目作用

内部仓储是综合信息平台中「门禁系统」业务域下的功能模块，对应页面目录 `src/pages/config_management/system/door_access_system/inner_storage`。

在项目中的主要作用：

- 作为「配置管理平台 → 系统管理 → 门禁系统 → 内部仓储」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
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

| 字段名          | 中文含义     | 作用说明                        |
| --------------- | ------------ | ------------------------------- |
| deviceGroupName | 所属子系统   | 模块表单/列表字段，详见页面配置 |
| subSystemName   | 所属区域     | 模块表单/列表字段，详见页面配置 |
| regionName      | 设备名称     | 模块表单/列表字段，详见页面配置 |
| level           | 初始人数     | 模块表单/列表字段，详见页面配置 |
| deviceName      | 设备名称     | 模块表单/列表字段，详见页面配置 |
| deviceCode      | 设备编号     | 模块表单/列表字段，详见页面配置 |
| deviceStatus    | 设备启用状态 | 模块表单/列表字段，详见页面配置 |
| storeName       | 库名称       | 模块表单/列表字段，详见页面配置 |
| deviceCodes     | 关联门设备   | 模块表单/列表字段，详见页面配置 |
| maxCount        | 最大容量     | 模块表单/列表字段，详见页面配置 |
| alarmCount      | 告警容量     | 模块表单/列表字段，详见页面配置 |
| inCount         | 初始人数     | 模块表单/列表字段，详见页面配置 |
| remark          | 备注         | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

- 新建/新增
- 编辑
- 删除
- 导出
- 导入
- 复制
- 左侧树筛选
- 启用/停用

---

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                                                         | 关系说明                                     |
| ---------------------------------------------------------------- | -------------------------------------------- |
| Access Information Maintenance（access_information_maintenance） | 同级功能模块，可共同构成「门禁系统」业务能力 |
| 门禁统计（access_statistics）                                    | 同级功能模块，可共同构成「门禁系统」业务能力 |
| door门禁同步（door_access_sync）                                 | 同级功能模块，可共同构成「门禁系统」业务能力 |
| 执勤信息（duty_info）                                            | 同级功能模块，可共同构成「门禁系统」业务能力 |
| 哨位岗位交接（guard_post_handover）                              | 同级功能模块，可共同构成「门禁系统」业务能力 |
| 入出仓储（in_out_storage）                                       | 同级功能模块，可共同构成「门禁系统」业务能力 |
| 安全检查（safety_check）                                         | 同级功能模块，可共同构成「门禁系统」业务能力 |

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

本模块（`inner_storage`）位于 `src/pages/config_management/system/door_access_system/inner_storage`，归属「门禁系统」。它负责「内部仓储」相关业务的页面交互与数据读写。维护本模块时，请同步关注接口契约、字段语义及与兄弟模块的数据一致性。

---

## 8. 接口清单

以下接口由本模块页面代码直接或通过 `@/services` Controller 调用，参数与响应 Schema 来自 `swaggerApi.json`（若可匹配）。

### 8.1 clearStoreInfo

| 项       | 内容                              |
| -------- | --------------------------------- |
| 接口路径 | `/store/clearStoreInfo`           |
| 请求方法 | `POST`                            |
| 前端封装 | `SystemController.clearStoreInfo` |
| 作用说明 | 见模块业务逻辑                    |

_未在 `swaggerApi.json` 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---

### 8.2 设置库设备出入库人数

| 项          | 内容                            |
| ----------- | ------------------------------- |
| 接口路径    | `/store/setStoreInfo`           |
| 请求方法    | `POST`                          |
| 前端封装    | `SystemController.setStoreInfo` |
| Swagger Tag | inventoryApi                    |
| 作用说明    | 设置库设备出入库人数            |

**请求参数（Body）：**

| 字段                 | 类型      | 说明 |
| -------------------- | --------- | ---- |
| `root`               | `array`   |      |
| `item[].id`          | `integer` |      |
| `item[].deviceCode`  | `string`  |      |
| `item[].enterCount`  | `integer` |      |
| `item[].outCount`    | `integer` |      |
| `item[].createdTime` | `string`  |      |
| `item[].updatedTime` | `string`  |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

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

### 8.4 获取出入库每日清除开关

| 项          | 内容                                     |
| ----------- | ---------------------------------------- |
| 接口路径    | `/store/getIsUpdateStoreCount`           |
| 请求方法    | `GET`                                    |
| 前端封装    | `SystemController.getIsUpdateStoreCount` |
| Swagger Tag | inventoryApi                             |
| 作用说明    | 获取出入库每日清除开关                   |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `integer` |      |

---

### 8.5 setIsUpdateStoreCount

| 项       | 内容                                     |
| -------- | ---------------------------------------- |
| 接口路径 | `未知`                                   |
| 请求方法 | `未知`                                   |
| 前端封装 | `SystemController.setIsUpdateStoreCount` |
| 作用说明 | 见模块业务逻辑                           |

_未在 `swaggerApi.json` 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---

### 8.6 获取内部人员出入库信息列表

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

### 8.7 新增内部人员出入库信息

| 项          | 内容                            |
| ----------- | ------------------------------- |
| 接口路径    | `/store/storeInfoAdd`           |
| 请求方法    | `POST`                          |
| 前端封装    | `SystemController.storeInfoAdd` |
| Swagger Tag | inventoryApi                    |
| 作用说明    | 新增内部人员出入库信息          |

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

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.8 修改内部人员出入库信息

| 项          | 内容                               |
| ----------- | ---------------------------------- |
| 接口路径    | `/store/storeInfoUpdate`           |
| 请求方法    | `POST`                             |
| 前端封装    | `SystemController.storeInfoUpdate` |
| Swagger Tag | inventoryApi                       |
| 作用说明    | 修改内部人员出入库信息             |

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

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.9 删除内部人员出入库信息

| 项          | 内容                               |
| ----------- | ---------------------------------- |
| 接口路径    | `/store/storeInfoDelete`           |
| 请求方法    | `POST`                             |
| 前端封装    | `SystemController.storeInfoDelete` |
| Swagger Tag | inventoryApi                       |
| 作用说明    | 删除内部人员出入库信息             |

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

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.10 获取门禁设备列表

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
