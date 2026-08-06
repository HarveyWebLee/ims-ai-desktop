# 设备注册索引（device_registry_index）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                                    |
| ------------------ | ----------------------------------------------------------------------- |
| 模块名称（中文）   | 设备注册索引                                                            |
| 模块名称（英文）   | Device Registry Index                                                   |
| 所属 Group（中文） | 历史数据                                                                |
| 所属 Group（英文） | History Data                                                            |
| Group ID           | `history_data`                                                          |
| 菜单位置           | 配置管理平台 → 配置管理 → 历史数据 → 设备注册索引                       |
| 路由路径           | `/config_management/config/history_data/device_registry_index`          |
| 页面目录           | `src/pages/config_management/config/history_data/device_registry_index` |

## 1. 模块定位与项目作用

设备注册索引是综合信息平台中「历史数据」业务域下的功能模块，对应页面目录 `src/pages/config_management/config/history_data/device_registry_index`。

在项目中的主要作用：

- 作为「配置管理平台 → 配置管理 → 历史数据 → 设备注册索引」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
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

| 字段名 | 中文含义 | 作用说明                        |
| ------ | -------- | ------------------------------- |
| isDel  | 索引状态 | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

- 删除
- 导出
- 导入
- 复制
- 启用/停用

---

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                                     | 关系说明                                     |
| -------------------------------------------- | -------------------------------------------- |
| 历史数据修复（history_data_repair）          | 同级功能模块，可共同构成「历史数据」业务能力 |
| 历史数据查询（history_query）                | 同级功能模块，可共同构成「历史数据」业务能力 |
| 历史数据统计（history_statistics）           | 同级功能模块，可共同构成「历史数据」业务能力 |
| 查询模板配置（query_template_configuration） | 同级功能模块，可共同构成「历史数据」业务能力 |
| 任务管理（task_manage）                      | 同级功能模块，可共同构成「历史数据」业务能力 |

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

本模块（`device_registry_index`）位于 `src/pages/config_management/config/history_data/device_registry_index`，归属「历史数据」。它负责「设备注册索引」相关业务的页面交互与数据读写。维护本模块时，请同步关注接口契约、字段语义及与兄弟模块的数据一致性。

---

## 8. 接口清单

以下接口由本模块页面代码直接或通过 `@/services` Controller 调用，参数与响应 Schema 来自 `swaggerApi.json`（若可匹配）。

### 8.1 软删除 t_device_mapping 中指定 dn 的记录（将 is_del 置为 1）

| 项          | 内容                                                         |
| ----------- | ------------------------------------------------------------ |
| 接口路径    | `/device/deleteDeviceMapping`                                |
| 请求方法    | `POST`                                                       |
| 前端封装    | `SystemController.deleteDeviceMapping`                       |
| baseURL     | `/api/appv2`                                                 |
| Swagger Tag | deviceManagementApi                                          |
| 作用说明    | 软删除 t_device_mapping 中指定 dn 的记录（将 is_del 置为 1） |

**Query/Path 参数：**

| 参数名 | 位置  | 必填 | 类型     | 说明     |
| ------ | ----- | ---- | -------- | -------- |
| `dn`   | query | 是   | `string` | 设备编号 |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `integer` |      |

---

### 8.2 恢复 t_device_mapping 中指定 dn 的已软删除记录（将 is_del 置为 0）

| 项          | 内容                                                               |
| ----------- | ------------------------------------------------------------------ |
| 接口路径    | `/api/app2/device/restoreDeviceMapping`                            |
| 请求方法    | `POST`                                                             |
| 前端封装    | `SystemController.restoreDeviceMapping`                            |
| baseURL     | `/api/appv2`                                                       |
| Swagger Tag | appGatewayApi                                                      |
| 作用说明    | 恢复 t_device_mapping 中指定 dn 的已软删除记录（将 is_del 置为 0） |

**Query/Path 参数：**

| 参数名 | 位置  | 必填 | 类型     | 说明     |
| ------ | ----- | ---- | -------- | -------- |
| `dn`   | query | 是   | `string` | 设备编号 |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `integer` |      |

---

### 8.3 查询设备列表（仅返回在 dm 库 t_device_mapping 中存在的设备，即 p_device 与 t_device_mapping 的交集）

| 项          | 内容                                                                                                 |
| ----------- | ---------------------------------------------------------------------------------------------------- |
| 接口路径    | `/device/getIndexedDeviceList`                                                                       |
| 请求方法    | `POST`                                                                                               |
| 前端封装    | `SystemController.getIndexedDeviceList`                                                              |
| baseURL     | `/api/appv2`                                                                                         |
| Swagger Tag | deviceManagementApi                                                                                  |
| 作用说明    | 查询设备列表（仅返回在 dm 库 t_device_mapping 中存在的设备，即 p_device 与 t_device_mapping 的交集） |

**请求参数（Body）：**

| 字段              | 类型             | 说明                   |
| ----------------- | ---------------- | ---------------------- |
| `deviceName`      | `string`         |                        |
| `deviceCode`      | `string`         |                        |
| `deviceGroupId`   | `integer`        |                        |
| `onlineStatus`    | `integer`        |                        |
| `subSystemId`     | `integer`        |                        |
| `commDeviceId`    | `integer`        |                        |
| `collectServerId` | `integer`        |                        |
| `templateId`      | `integer`        |                        |
| `commModel`       | `array<integer>` | 通信模式，支持多值过滤 |
| `page`            | `integer`        |                        |
| `size`            | `integer`        |                        |

**响应体：**

| 字段                                  | 类型            | 说明                                 |
| ------------------------------------- | --------------- | ------------------------------------ |
| `code`                                | `integer`       |                                      |
| `message`                             | `string`        |                                      |
| `data`                                | `object`        |                                      |
| `data.current`                        | `integer`       |                                      |
| `data.pages`                          | `integer`       |                                      |
| `data.size`                           | `integer`       |                                      |
| `data.total`                          | `integer`       |                                      |
| `data.records`                        | `array<object>` |                                      |
| `data.records[].id`                   | `integer`       |                                      |
| `data.records[].deviceName`           | `string`        |                                      |
| `data.records[].deviceCode`           | `string`        |                                      |
| `data.records[].subSystemId`          | `integer`       |                                      |
| `data.records[].subSystemName`        | `string`        |                                      |
| `data.records[].deviceGroupId`        | `integer`       |                                      |
| `data.records[].deviceGroupName`      | `string`        |                                      |
| `data.records[].commDeviceId`         | `integer`       |                                      |
| `data.records[].commDeviceCode`       | `string`        |                                      |
| `data.records[].commDeviceName`       | `string`        |                                      |
| `data.records[].collectServerId`      | `integer`       |                                      |
| `data.records[].collectServerName`    | `string`        |                                      |
| `data.records[].deviceCategoryId`     | `integer`       |                                      |
| `data.records[].deviceCategoryName`   | `string`        |                                      |
| `data.records[].manufacturer`         | `string`        |                                      |
| `data.records[].model`                | `string`        |                                      |
| `data.records[].ipAddress`            | `string`        |                                      |
| `data.records[].port`                 | `string`        |                                      |
| `data.records[].userName`             | `string`        |                                      |
| `data.records[].password`             | `string`        |                                      |
| `data.records[].location`             | `string`        |                                      |
| `data.records[].firstUseTime`         | `string`        |                                      |
| `data.records[].parentDeviceId`       | `integer`       |                                      |
| `data.records[].parentDeviceName`     | `string`        |                                      |
| `data.records[].srcZoneId`            | `integer`       |                                      |
| `data.records[].secZoneName`          | `string`        |                                      |
| `data.records[].maintenanceSituation` | `string`        |                                      |
| `data.records[].repairSituation`      | `string`        |                                      |
| `data.records[].devicePic`            | `string`        |                                      |
| `data.records[].remark`               | `string`        |                                      |
| `data.records[].deviceStatus`         | `integer`       | 增加设备是否启用和报警间隔、在线状态 |
| `data.records[].alertInterval`        | `integer`       |                                      |
| `data.records[].onlineStatus`         | `integer`       |                                      |
| `data.records[].onlineStatusName`     | `string`        |                                      |
| `data.records[].protocolId`           | `integer`       | 增加协议                             |
| `data.records[].protocolName`         | `string`        |                                      |
| `data.records[].protocolParams`       | `string`        |                                      |
| `data.records[].regionId`             | `integer`       | 增加区域位置信息                     |
| `data.records[].regionName`           | `string`        |                                      |
| `data.records[].faultStatus`          | `integer`       | 增加设备故障状态                     |
| `data.records[].configInfo`           | `string`        | 增加组态设备图元配置信息             |
| `data.records[].isTemplate`           | `integer`       | 新增是否模板设备字段                 |
| `data.records[].templateId`           | `integer`       | 新增模板设备id                       |
| `data.records[].templateName`         | `string`        |                                      |
| `data.records[].commModel`            | `integer`       | 新增通信模式字段                     |
| `data.records[].thirdDeviceId`        | `string`        |                                      |
| `data.records[].variableList`         | `array<object>` | 变量列表                             |

---
