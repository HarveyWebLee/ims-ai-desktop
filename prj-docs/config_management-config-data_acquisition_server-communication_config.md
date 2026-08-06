# 通信网关（communication_config）知识库

> 上级模块索引：[data_acquisition_server.md](./data_acquisition_server.md) · 总索引：[README.md](./README.md) · 页面总表：[TOTAL-MODULE.md](./TOTAL-MODULE.md)

## 0. 路由与归属信息

| 项                 | 内容                                                                              |
| ------------------ | --------------------------------------------------------------------------------- |
| 模块名称（中文）   | 通信网关                                                                          |
| 模块名称（英文）   | Communication Config                                                              |
| 所属 Group（中文） | 数采服务器                                                                        |
| 所属 Group（英文） | Data Acquisition Server                                                           |
| Group ID           | `data_acquisition_server`                                                         |
| 菜单位置           | 配置管理平台 → 配置管理 → 数采服务器 → 通信网关                                   |
| 路由路径           | `/config_management/config/communication_config`                                  |
| 页面目录           | `src/pages/config_management/config/data_acquisition_server/communication_config` |

## 1. 模块定位与项目作用

通信配置是综合信息平台中「数采服务器」业务域下的功能模块，对应页面目录 `src/pages/config_management/config/data_acquisition_server/communication_config`。

在项目中的主要作用：

- 作为「配置管理平台 → 配置管理 → 数采服务器 → 通信配置」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
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

| 字段名               | 中文含义       | 作用说明                        |
| -------------------- | -------------- | ------------------------------- |
| subSystemName        | 所属区域       | 模块表单/列表字段，详见页面配置 |
| regionName           | 设备名称       | 模块表单/列表字段，详见页面配置 |
| manufacturer         | 规格型号       | 模块表单/列表字段，详见页面配置 |
| id                   | 主键ID         | 模块表单/列表字段，详见页面配置 |
| deviceGroupId        | 设备分组       | 模块表单/列表字段，详见页面配置 |
| deviceGroupName      | 设备分组       | 模块表单/列表字段，详见页面配置 |
| subSystemId          | 所属子系统     | 模块表单/列表字段，详见页面配置 |
| deviceName           | 设备名称       | 模块表单/列表字段，详见页面配置 |
| deviceCode           | 设备编号       | 模块表单/列表字段，详见页面配置 |
| deviceStatus         | 设备启用状态   | 模块表单/列表字段，详见页面配置 |
| alertInterval        | 告警间隔(分钟) | 模块表单/列表字段，详见页面配置 |
| onlineStatus         | 设备在线状态   | 模块表单/列表字段，详见页面配置 |
| onlineStatusName     | 设备在线状态   | 模块表单/列表字段，详见页面配置 |
| regionId             | 所属区域       | 模块表单/列表字段，详见页面配置 |
| commModel            | 通信模式       | 模块表单/列表字段，详见页面配置 |
| collectServerId      | 代理设备       | 模块表单/列表字段，详见页面配置 |
| collectServerName    | 代理设备       | 模块表单/列表字段，详见页面配置 |
| deviceCategoryId     | 监控设备类型   | 模块表单/列表字段，详见页面配置 |
| deviceCategoryName   | 监控设备类型   | 模块表单/列表字段，详见页面配置 |
| model                | 规格型号       | 模块表单/列表字段，详见页面配置 |
| ipAddress            | IP地址         | 模块表单/列表字段，详见页面配置 |
| location             | 所在位置       | 模块表单/列表字段，详见页面配置 |
| firstUseTime         | 首次使用时间   | 模块表单/列表字段，详见页面配置 |
| remark               | 备注           | 模块表单/列表字段，详见页面配置 |
| devicePic            | 照片           | 模块表单/列表字段，详见页面配置 |
| maintenanceSituation | 保养情况       | 模块表单/列表字段，详见页面配置 |
| repairSituation      | 检修情况       | 模块表单/列表字段，详见页面配置 |
| protocolId           | 通讯协议       | 模块表单/列表字段，详见页面配置 |
| protocolName         | 通讯协议       | 模块表单/列表字段，详见页面配置 |
| protocolParams       | 协议参数       | 模块表单/列表字段，详见页面配置 |
| file                 | file           | 模块表单/列表字段，详见页面配置 |
| 图片                 | 图片           | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

- 新建/新增
- 编辑
- 删除
- 导出
- 导入
- 批量修改导入
- 复制
- 左侧树筛选
- 启用/停用

---

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                      | 关系说明                                       |
| ----------------------------- | ---------------------------------------------- |
| 数采服务器（das）             | 同级功能模块，可共同构成「数采服务器」业务能力 |
| 服务组件（service_component） | 同级功能模块，可共同构成「数采服务器」业务能力 |

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

本模块（`communication_config`）位于 `src/pages/config_management/config/data_acquisition_server/communication_config`，归属「数采服务器」。它负责「通信配置」相关业务的页面交互与数据读写。维护本模块时，请同步关注接口契约、字段语义及与兄弟模块的数据一致性。

---

## 8. 接口清单

以下接口由本模块页面代码直接或通过 `@/services` Controller 调用，参数与响应 Schema 来自平台 OpenAPI（若可匹配）。

### 8.1 exportDevice1

| 项       | 内容                             |
| -------- | -------------------------------- |
| 接口路径 | `/device/exportDevice1`          |
| 请求方法 | `GET`                            |
| 前端封装 | `SystemController.exportDevice1` |
| 作用说明 | 见模块业务逻辑                   |

_未在平台 OpenAPI 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---

### 8.2 获取设备列表

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

### 8.3 导出设备

| 项          | 内容                            |
| ----------- | ------------------------------- |
| 接口路径    | `/device/exportDevice`          |
| 请求方法    | `GET`                           |
| 前端封装    | `SystemController.exportDevice` |
| Swagger Tag | deviceManagementApi             |
| 作用说明    | 导出设备                        |

**Query/Path 参数：**

| 参数名            | 位置  | 必填 | 类型     | 说明                                       |
| ----------------- | ----- | ---- | -------- | ------------------------------------------ |
| `page`            | query | 是   | `string` |                                            |
| `size`            | query | 是   | `string` |                                            |
| `search`          | query | 否   | `string` |                                            |
| `fieldList[0]`    | query | 否   | `string` |                                            |
| `sorter[0].order` | query | 否   | `string` |                                            |
| `sorter[0].field` | query | 否   | `string` |                                            |
| `deviceCode`      | query | 否   | `string` |                                            |
| `deviceName`      | query | 否   | `string` |                                            |
| `deviceGroupId`   | query | 否   | `string` |                                            |
| `subSystemId`     | query | 否   | `string` |                                            |
| `regionId`        | query | 否   | `string` |                                            |
| `deviceStatus`    | query | 否   | `string` |                                            |
| `onlineStatus`    | query | 否   | `string` |                                            |
| `commDeviceId`    | query | 否   | `string` |                                            |
| `collectServerId` | query | 否   | `string` |                                            |
| `deviceCombId`    | query | 否   | `string` | 新增组合设备查询                           |
| `isTemplate`      | query | 否   | `string` | 新增是否模板设备查询                       |
| `containSubLevel` | query | 否   | `string` | 新增是否包含下级查询                       |
| `commModel[0]`    | query | 否   | `string` | 新增通信模式字段（1-直接，2-间接，3-网关） |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

---

### 8.4 添加设备

| 项          | 内容                         |
| ----------- | ---------------------------- |
| 接口路径    | `/device/addDevice`          |
| 请求方法    | `POST`                       |
| 前端封装    | `SystemController.addDevice` |
| Swagger Tag | deviceManagementApi          |
| 作用说明    | 添加设备                     |

**请求参数（Body）：**

| 字段                   | 类型             | 说明                                     |
| ---------------------- | ---------------- | ---------------------------------------- |
| `id`                   | `integer`        |                                          |
| `deviceName`           | `string`         |                                          |
| `deviceCode`           | `string`         |                                          |
| `subSystemId`          | `integer`        |                                          |
| `deviceGroupId`        | `integer`        |                                          |
| `commDeviceId`         | `integer`        |                                          |
| `collectServerId`      | `integer`        |                                          |
| `deviceCategoryId`     | `integer`        |                                          |
| `manufacturer`         | `string`         |                                          |
| `model`                | `string`         |                                          |
| `ipAddress`            | `string`         |                                          |
| `port`                 | `string`         |                                          |
| `userName`             | `string`         |                                          |
| `password`             | `string`         |                                          |
| `location`             | `string`         |                                          |
| `firstUseTime`         | `string`         |                                          |
| `parentDeviceId`       | `integer`        |                                          |
| `srcZoneId`            | `integer`        |                                          |
| `maintenanceSituation` | `string`         |                                          |
| `repairSituation`      | `string`         |                                          |
| `devicePic`            | `string`         |                                          |
| `remark`               | `string`         |                                          |
| `deviceStatus`         | `integer`        | 增加设备是否启用和报警间隔、设备在线状态 |
| `alertInterval`        | `integer`        |                                          |
| `onlineStatus`         | `integer`        |                                          |
| `ids`                  | `array<integer>` |                                          |
| `protocolId`           | `integer`        | 增加协议                                 |
| `protocolParams`       | `string`         |                                          |
| `regionId`             | `integer`        | 增加区域位置信息                         |
| `faultStatus`          | `integer`        | 增加设备故障状态                         |
| `configInfo`           | `string`         | 增加组态设备图元配置信息                 |
| `isTemplate`           | `integer`        | 新增是否模板设备字段                     |
| `templateId`           | `integer`        | 新增模板设备id                           |
| `commModel`            | `integer`        | 新增通信模式字段                         |
| `thirdDeviceId`        | `string`         | 新增第三方设备Id字段                     |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.5 更新设备

| 项          | 内容                            |
| ----------- | ------------------------------- |
| 接口路径    | `/device/updateDevice`          |
| 请求方法    | `POST`                          |
| 前端封装    | `SystemController.updateDevice` |
| Swagger Tag | deviceManagementApi             |
| 作用说明    | 更新设备                        |

**请求参数（Body）：**

| 字段                   | 类型             | 说明                                     |
| ---------------------- | ---------------- | ---------------------------------------- |
| `id`                   | `integer`        |                                          |
| `deviceName`           | `string`         |                                          |
| `deviceCode`           | `string`         |                                          |
| `subSystemId`          | `integer`        |                                          |
| `deviceGroupId`        | `integer`        |                                          |
| `commDeviceId`         | `integer`        |                                          |
| `collectServerId`      | `integer`        |                                          |
| `deviceCategoryId`     | `integer`        |                                          |
| `manufacturer`         | `string`         |                                          |
| `model`                | `string`         |                                          |
| `ipAddress`            | `string`         |                                          |
| `port`                 | `string`         |                                          |
| `userName`             | `string`         |                                          |
| `password`             | `string`         |                                          |
| `location`             | `string`         |                                          |
| `firstUseTime`         | `string`         |                                          |
| `parentDeviceId`       | `integer`        |                                          |
| `srcZoneId`            | `integer`        |                                          |
| `maintenanceSituation` | `string`         |                                          |
| `repairSituation`      | `string`         |                                          |
| `devicePic`            | `string`         |                                          |
| `remark`               | `string`         |                                          |
| `deviceStatus`         | `integer`        | 增加设备是否启用和报警间隔、设备在线状态 |
| `alertInterval`        | `integer`        |                                          |
| `onlineStatus`         | `integer`        |                                          |
| `ids`                  | `array<integer>` |                                          |
| `protocolId`           | `integer`        | 增加协议                                 |
| `protocolParams`       | `string`         |                                          |
| `regionId`             | `integer`        | 增加区域位置信息                         |
| `faultStatus`          | `integer`        | 增加设备故障状态                         |
| `configInfo`           | `string`         | 增加组态设备图元配置信息                 |
| `isTemplate`           | `integer`        | 新增是否模板设备字段                     |
| `templateId`           | `integer`        | 新增模板设备id                           |
| `commModel`            | `integer`        | 新增通信模式字段                         |
| `thirdDeviceId`        | `string`         | 新增第三方设备Id字段                     |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.6 删除设备

| 项          | 内容                            |
| ----------- | ------------------------------- |
| 接口路径    | `/device/deleteDevice`          |
| 请求方法    | `POST`                          |
| 前端封装    | `SystemController.deleteDevice` |
| Swagger Tag | deviceManagementApi             |
| 作用说明    | 删除设备                        |

**请求参数（Body）：**

| 字段                   | 类型             | 说明                                     |
| ---------------------- | ---------------- | ---------------------------------------- |
| `id`                   | `integer`        |                                          |
| `deviceName`           | `string`         |                                          |
| `deviceCode`           | `string`         |                                          |
| `subSystemId`          | `integer`        |                                          |
| `deviceGroupId`        | `integer`        |                                          |
| `commDeviceId`         | `integer`        |                                          |
| `collectServerId`      | `integer`        |                                          |
| `deviceCategoryId`     | `integer`        |                                          |
| `manufacturer`         | `string`         |                                          |
| `model`                | `string`         |                                          |
| `ipAddress`            | `string`         |                                          |
| `port`                 | `string`         |                                          |
| `userName`             | `string`         |                                          |
| `password`             | `string`         |                                          |
| `location`             | `string`         |                                          |
| `firstUseTime`         | `string`         |                                          |
| `parentDeviceId`       | `integer`        |                                          |
| `srcZoneId`            | `integer`        |                                          |
| `maintenanceSituation` | `string`         |                                          |
| `repairSituation`      | `string`         |                                          |
| `devicePic`            | `string`         |                                          |
| `remark`               | `string`         |                                          |
| `deviceStatus`         | `integer`        | 增加设备是否启用和报警间隔、设备在线状态 |
| `alertInterval`        | `integer`        |                                          |
| `onlineStatus`         | `integer`        |                                          |
| `ids`                  | `array<integer>` |                                          |
| `protocolId`           | `integer`        | 增加协议                                 |
| `protocolParams`       | `string`         |                                          |
| `regionId`             | `integer`        | 增加区域位置信息                         |
| `faultStatus`          | `integer`        | 增加设备故障状态                         |
| `configInfo`           | `string`         | 增加组态设备图元配置信息                 |
| `isTemplate`           | `integer`        | 新增是否模板设备字段                     |
| `templateId`           | `integer`        | 新增模板设备id                           |
| `commModel`            | `integer`        | 新增通信模式字段                         |
| `thirdDeviceId`        | `string`         | 新增第三方设备Id字段                     |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.7 importDevice2

| 项       | 内容                             |
| -------- | -------------------------------- |
| 接口路径 | `/device/importDevice/2`         |
| 请求方法 | `POST`                           |
| 前端封装 | `SystemController.importDevice2` |
| 作用说明 | 见模块业务逻辑                   |

_未在平台 OpenAPI 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---

### 8.8 batchUpdateDevice2

| 项       | 内容                                  |
| -------- | ------------------------------------- |
| 接口路径 | `/device/batchUpdateDevice/2`         |
| 请求方法 | `POST`                                |
| 前端封装 | `SystemController.batchUpdateDevice2` |
| 作用说明 | 见模块业务逻辑                        |

_未在平台 OpenAPI 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---

### 8.9 复制设备、设备变量、报警规则

| 项          | 内容                                |
| ----------- | ----------------------------------- |
| 接口路径    | `/device/copyDeviceAndVar`          |
| 请求方法    | `POST`                              |
| 前端封装    | `SystemController.copyDeviceAndVar` |
| Swagger Tag | deviceManagementApi                 |
| 作用说明    | 复制设备、设备变量、报警规则        |

**请求参数（Body）：**

| 字段            | 类型      | 说明 |
| --------------- | --------- | ---- |
| `oldDeviceId`   | `integer` |      |
| `newDeviceCode` | `string`  |      |
| `newDeviceName` | `string`  |      |
| `isTemplate`    | `integer` |      |
| `templateId`    | `integer` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.10 获取设备分组树

| 项          | 内容                                  |
| ----------- | ------------------------------------- |
| 接口路径    | `/device/getDeviceGroupTree`          |
| 请求方法    | `POST`                                |
| 前端封装    | `SystemController.getDeviceGroupTree` |
| Swagger Tag | deviceManagementApi                   |
| 作用说明    | 获取设备分组树                        |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段         | 类型            | 说明 |
| ------------ | --------------- | ---- |
| `code`       | `integer`       |      |
| `message`    | `string`        |      |
| `data`       | `array<object>` |      |
| `data[].key` | `object`        |      |

---

### 8.11 获取菜单树

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

### 8.12 获取区域树

| 项          | 内容                             |
| ----------- | -------------------------------- |
| 接口路径    | `/region/getRegionTree`          |
| 请求方法    | `GET`                            |
| 前端封装    | `SystemController.getRegionTree` |
| Swagger Tag | regionManagementApi              |
| 作用说明    | 获取区域树                       |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段         | 类型            | 说明 |
| ------------ | --------------- | ---- |
| `code`       | `integer`       |      |
| `message`    | `string`        |      |
| `data`       | `array<object>` |      |
| `data[].key` | `object`        |      |

---

### 8.13 获取数据采集服务器分页列表

| 项          | 内容                                    |
| ----------- | --------------------------------------- |
| 接口路径    | `/server/getCollectServerList`          |
| 请求方法    | `POST`                                  |
| 前端封装    | `SystemController.getCollectServerList` |
| Swagger Tag | serverManagementApi                     |
| 作用说明    | 获取数据采集服务器分页列表              |

**请求参数（Body）：**

| 字段        | 类型            | 说明 |
| ----------- | --------------- | ---- |
| `page`      | `integer`       |      |
| `size`      | `integer`       |      |
| `search`    | `string`        |      |
| `fieldList` | `array<string>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.14 获取设备类型树

| 项          | 内容                                     |
| ----------- | ---------------------------------------- |
| 接口路径    | `/device/getDeviceCategoryTree`          |
| 请求方法    | `POST`                                   |
| 前端封装    | `SystemController.getDeviceCategoryTree` |
| Swagger Tag | deviceManagementApi                      |
| 作用说明    | 获取设备类型树                           |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段         | 类型            | 说明 |
| ------------ | --------------- | ---- |
| `code`       | `integer`       |      |
| `message`    | `string`        |      |
| `data`       | `array<object>` |      |
| `data[].key` | `object`        |      |

---

### 8.15 获取通讯协议字典

| 项          | 内容                              |
| ----------- | --------------------------------- |
| 接口路径    | `/server/getProtocolDic`          |
| 请求方法    | `GET`                             |
| 前端封装    | `SystemController.getProtocolDic` |
| Swagger Tag | serverManagementApi               |
| 作用说明    | 获取通讯协议字典                  |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段           | 类型            | 说明 |
| -------------- | --------------- | ---- |
| `code`         | `integer`       |      |
| `message`      | `string`        |      |
| `data`         | `array<object>` |      |
| `data[].id`    | `integer`       |      |
| `data[].name`  | `string`        |      |
| `data[].cname` | `string`        |      |

---

### 8.16 获取通信协议参数

| 项          | 内容                                 |
| ----------- | ------------------------------------ |
| 接口路径    | `/server/getProtocolParams`          |
| 请求方法    | `POST`                               |
| 前端封装    | `SystemController.getProtocolParams` |
| Swagger Tag | serverManagementApi                  |
| 作用说明    | 获取通信协议参数                     |

**请求参数（Body）：**

| 字段                  | 类型             | 说明                 |
| --------------------- | ---------------- | -------------------- |
| `id`                  | `integer`        |                      |
| `collectServerId`     | `integer`        |                      |
| `commDeviceName`      | `string`         |                      |
| `commDeviceCode`      | `string`         |                      |
| `subSystemId`         | `integer`        |                      |
| `manufacturer`        | `string`         |                      |
| `model`               | `string`         |                      |
| `ipAddress`           | `string`         |                      |
| `location`            | `string`         |                      |
| `firstTime`           | `string`         |                      |
| `remark`              | `string`         |                      |
| `monitorDeviceTypeId` | `integer`        |                      |
| `commDevicePicture`   | `string`         |                      |
| `protocolId`          | `integer`        |                      |
| `protocolParams`      | `string`         |                      |
| `ids`                 | `array<integer>` |                      |
| `onlineStatus`        | `integer`        | 增加通信设备在线状态 |
| `deviceStatus`        | `integer`        | 增加通信设备启用状态 |

**响应体：**

| 字段         | 类型            | 说明 |
| ------------ | --------------- | ---- |
| `code`       | `integer`       |      |
| `message`    | `string`        |      |
| `data`       | `array<object>` |      |
| `data[].key` | `object`        |      |

---
