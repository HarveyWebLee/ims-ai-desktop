# 入出仓储（in_out_storage）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                                   |
| ------------------ | ---------------------------------------------------------------------- |
| 模块名称（中文）   | 入出仓储                                                               |
| 模块名称（英文）   | In Out Storage                                                         |
| 所属 Group（中文） | 门禁系统                                                               |
| 所属 Group（英文） | Door Access System                                                     |
| Group ID           | `door_access_system`                                                   |
| 菜单位置           | 配置管理平台 → 系统管理 → 门禁系统 → 入出仓储                          |
| 路由路径           | `/config_management/system/door_access_system/in_out_storage`          |
| 页面目录           | `src/pages/config_management/system/door_access_system/in_out_storage` |

## 1. 模块定位与项目作用

入出仓储是综合信息平台中「门禁系统」业务域下的功能模块，对应页面目录 `src/pages/config_management/system/door_access_system/in_out_storage`。

在项目中的主要作用：

- 作为「配置管理平台 → 系统管理 → 门禁系统 → 入出仓储」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
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

| 字段名          | 中文含义         | 作用说明                        |
| --------------- | ---------------- | ------------------------------- |
| deviceGroupName | 所属子系统       | 模块表单/列表字段，详见页面配置 |
| subSystemName   | 所属区域         | 模块表单/列表字段，详见页面配置 |
| regionName      | 设备名称         | 模块表单/列表字段，详见页面配置 |
| deviceCode      | 门名称           | 模块表单/列表字段，详见页面配置 |
| deviceName      | 申请单位         | 模块表单/列表字段，详见页面配置 |
| teamLeaderId    | 带队人           | 模块表单/列表字段，详见页面配置 |
| teamLeaderName  | 职务             | 模块表单/列表字段，详见页面配置 |
| position        | 活动区域         | 模块表单/列表字段，详见页面配置 |
| outTime         | 入库人数         | 模块表单/列表字段，详见页面配置 |
| deviceStatus    | 设备启用状态     | 模块表单/列表字段，详见页面配置 |
| applyUnit       | 申请单位         | 模块表单/列表字段，详见页面配置 |
| activeArea      | 活动区域         | 模块表单/列表字段，详见页面配置 |
| inTime          | 入库时间         | 模块表单/列表字段，详见页面配置 |
| inCount         | 入库人数         | 模块表单/列表字段，详见页面配置 |
| inReason        | 入库事由         | 模块表单/列表字段，详见页面配置 |
| allPersonInfo   | 随行入库人员信息 | 模块表单/列表字段，详见页面配置 |

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
| 内部仓储（inner_storage）                                        | 同级功能模块，可共同构成「门禁系统」业务能力 |
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

本模块（`in_out_storage`）位于 `src/pages/config_management/system/door_access_system/in_out_storage`，归属「门禁系统」。它负责「入出仓储」相关业务的页面交互与数据读写。维护本模块时，请同步关注接口契约、字段语义及与兄弟模块的数据一致性。

---

## 8. 接口清单

以下接口由本模块页面代码直接或通过 `@/services` Controller 调用，参数与响应 Schema 来自 `swaggerApi.json`（若可匹配）。

### 8.1 出入库信息分页列表

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

### 8.2 添加出入库信息

| 项          | 内容                                  |
| ----------- | ------------------------------------- |
| 接口路径    | `/store/addStorePersonInfo`           |
| 请求方法    | `POST`                                |
| 前端封装    | `SystemController.addStorePersonInfo` |
| Swagger Tag | inventoryApi                          |
| 作用说明    | 添加出入库信息                        |

**请求参数（Body）：**

| 字段                   | 类型             | 说明 |
| ---------------------- | ---------------- | ---- |
| `id`                   | `integer`        |      |
| `deviceCode`           | `string`         |      |
| `deviceName`           | `string`         |      |
| `applyUnit`            | `string`         |      |
| `teamLeader`           | `string`         |      |
| `position`             | `string`         |      |
| `activeArea`           | `string`         |      |
| `inTime`               | `string`         |      |
| `outTime`              | `string`         |      |
| `inCount`              | `integer`        |      |
| `inReason`             | `string`         |      |
| `swipeInfo`            | `string`         |      |
| `allPersonInfo`        | `array<object>`  |      |
| `allPersonInfo[].name` | `string`         |      |
| `allPersonInfo[].type` | `string`         |      |
| `ids`                  | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.3 修改出入库信息

| 项          | 内容                                     |
| ----------- | ---------------------------------------- |
| 接口路径    | `/store/updateStorePersonInfo`           |
| 请求方法    | `POST`                                   |
| 前端封装    | `SystemController.updateStorePersonInfo` |
| Swagger Tag | inventoryApi                             |
| 作用说明    | 修改出入库信息                           |

**请求参数（Body）：**

| 字段                   | 类型             | 说明 |
| ---------------------- | ---------------- | ---- |
| `id`                   | `integer`        |      |
| `deviceCode`           | `string`         |      |
| `deviceName`           | `string`         |      |
| `applyUnit`            | `string`         |      |
| `teamLeader`           | `string`         |      |
| `position`             | `string`         |      |
| `activeArea`           | `string`         |      |
| `inTime`               | `string`         |      |
| `outTime`              | `string`         |      |
| `inCount`              | `integer`        |      |
| `inReason`             | `string`         |      |
| `swipeInfo`            | `string`         |      |
| `allPersonInfo`        | `array<object>`  |      |
| `allPersonInfo[].name` | `string`         |      |
| `allPersonInfo[].type` | `string`         |      |
| `ids`                  | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.4 删除出入库信息

| 项          | 内容                                     |
| ----------- | ---------------------------------------- |
| 接口路径    | `/store/deleteStorePersonInfo`           |
| 请求方法    | `POST`                                   |
| 前端封装    | `SystemController.deleteStorePersonInfo` |
| Swagger Tag | inventoryApi                             |
| 作用说明    | 删除出入库信息                           |

**请求参数（Body）：**

| 字段                   | 类型             | 说明 |
| ---------------------- | ---------------- | ---- |
| `id`                   | `integer`        |      |
| `deviceCode`           | `string`         |      |
| `deviceName`           | `string`         |      |
| `applyUnit`            | `string`         |      |
| `teamLeader`           | `string`         |      |
| `position`             | `string`         |      |
| `activeArea`           | `string`         |      |
| `inTime`               | `string`         |      |
| `outTime`              | `string`         |      |
| `inCount`              | `integer`        |      |
| `inReason`             | `string`         |      |
| `swipeInfo`            | `string`         |      |
| `allPersonInfo`        | `array<object>`  |      |
| `allPersonInfo[].name` | `string`         |      |
| `allPersonInfo[].type` | `string`         |      |
| `ids`                  | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.5 获取门禁设备列表

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

### 8.6 获取门禁人员列表

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
