# 手动撤布防（manual_cycle_disarm）知识库

> 上级模块索引：[perimeter_setting.md](./perimeter_setting.md) · 总索引：[README.md](./README.md) · 页面总表：[TOTAL-MODULE.md](./TOTAL-MODULE.md)

## 0. 路由与归属信息

| 项                 | 内容                                                                       |
| ------------------ | -------------------------------------------------------------------------- |
| 模块名称（中文）   | 手动撤布防                                                                 |
| 模块名称（英文）   | Manual Cycle Disarm                                                        |
| 所属 Group（中文） | 周界防区设定                                                               |
| 所属 Group（英文） | Perimeter Zone Setting                                                     |
| Group ID           | `perimeter_setting`                                                        |
| 菜单位置           | 配置管理平台 → 配置管理 → 周界防区设定 → 手动撤布防                        |
| 路由路径           | `/config_management/config/manual_cycle_disarm`                            |
| 页面目录           | `src/pages/config_management/config/perimeter_setting/manual_cycle_disarm` |

## 1. 模块定位与项目作用

手动周期撤防是综合信息平台中「周界防区设定」业务域下的功能模块，对应页面目录 `src/pages/config_management/config/perimeter_setting/manual_cycle_disarm`。

在项目中的主要作用：

- 作为「配置管理平台 → 配置管理 → 周界防区设定 → 手动周期撤防」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
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

| 字段名            | 中文含义            | 作用说明                        |
| ----------------- | ------------------- | ------------------------------- |
| deviceName        | currentStatus       | 模块表单/列表字段，详见页面配置 |
| defenceStatusName | defenceStatusCheck  | 模块表单/列表字段，详见页面配置 |
| areaId            | defenceArea         | 模块表单/列表字段，详见页面配置 |
| defenceAreaId     | defenceArea         | 模块表单/列表字段，详见页面配置 |
| onlineStatus      | currentStatus       | 模块表单/列表字段，详见页面配置 |
| defenceStatus     | defenceAreaStatus   | 模块表单/列表字段，详见页面配置 |
| validStatusName   | defenceStatusCheck  | 模块表单/列表字段，详见页面配置 |
| manual_setting    | manualSetting       | 模块表单/列表字段，详见页面配置 |
| modelType         | modeSwitch          | 模块表单/列表字段，详见页面配置 |
| defence_cycle     | defenceCycleSetting | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

- 导出
- 导入
- 复制
- 启用/停用

---

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                      | 关系说明                                         |
| ----------------------------- | ------------------------------------------------ |
| 撤防记录（evacuation_record） | 同级功能模块，可共同构成「周界防区设定」业务能力 |
| 防区分组（group）             | 同级功能模块，可共同构成「周界防区设定」业务能力 |
| 维护（maintenance）           | 同级功能模块，可共同构成「周界防区设定」业务能力 |

### 5.2 上游依赖 / 下游消费

- **上游**：根据本页接口与字段引用，上游主要为：用户及参数管理（`user`）、基础数据（`basedata`）。另可能依赖登录会话与菜单授权（用户及参数管理）。
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

本模块（`manual_cycle_disarm`）位于 `src/pages/config_management/config/perimeter_setting/manual_cycle_disarm`，归属「周界防区设定」。它负责「手动周期撤防」相关业务的页面交互与数据读写。维护本模块时，请同步关注接口契约、字段语义及与兄弟模块的数据一致性。

---

## 8. 接口清单

以下接口由本模块页面代码直接或通过 `@/services` Controller 调用，参数与响应 Schema 来自平台 OpenAPI（若可匹配）。

### 8.1 获取全部防区

| 项          | 内容                                   |
| ----------- | -------------------------------------- |
| 接口路径    | `/defenceArea/getDefenceAreaArray`     |
| 请求方法    | `POST`                                 |
| 前端封装    | `SystemController.getDefenceAreaArray` |
| Swagger Tag | defenseAreaApi                         |
| 作用说明    | 获取全部防区                           |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.2 获取撤布防设置列表

| 项          | 内容                                    |
| ----------- | --------------------------------------- |
| 接口路径    | `/defenceArea/getDefenceConfigList`     |
| 请求方法    | `POST`                                  |
| 前端封装    | `SystemController.getDefenceConfigList` |
| Swagger Tag | defenseAreaApi                          |
| 作用说明    | 获取撤布防设置列表                      |

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
| `areaName`       | `string`        |      |
| `areaId`         | `integer`       |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.3 手动和周期模式切换

| 项          | 内容                           |
| ----------- | ------------------------------ |
| 接口路径    | `/defenceArea/modelChange`     |
| 请求方法    | `POST`                         |
| 前端封装    | `SystemController.modelChange` |
| Swagger Tag | defenseAreaApi                 |
| 作用说明    | 手动和周期模式切换             |

**请求参数（Body）：**

| 字段             | 类型             | 说明 |
| ---------------- | ---------------- | ---- |
| `defenceAreaId`  | `integer`        |      |
| `deviceCode`     | `string`         |      |
| `modelType`      | `integer`        |      |
| `defenceCycle`   | `string`         |      |
| `username`       | `string`         |      |
| `defenceStatus`  | `integer`        |      |
| `onlineStatus`   | `integer`        |      |
| `defenceAreaIds` | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.4 批量布防

| 项          | 内容                            |
| ----------- | ------------------------------- |
| 接口路径    | `/defenceArea/defenceBatch`     |
| 请求方法    | `POST`                          |
| 前端封装    | `SystemController.defenceBatch` |
| Swagger Tag | defenseAreaApi                  |
| 作用说明    | 批量布防                        |

**请求参数（Body）：**

| 字段             | 类型             | 说明 |
| ---------------- | ---------------- | ---- |
| `defenceAreaId`  | `integer`        |      |
| `deviceCode`     | `string`         |      |
| `modelType`      | `integer`        |      |
| `defenceCycle`   | `string`         |      |
| `username`       | `string`         |      |
| `defenceStatus`  | `integer`        |      |
| `onlineStatus`   | `integer`        |      |
| `defenceAreaIds` | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.5 批量撤防

| 项          | 内容                             |
| ----------- | -------------------------------- |
| 接口路径    | `/defenceArea/withdrawBatch`     |
| 请求方法    | `POST`                           |
| 前端封装    | `SystemController.withdrawBatch` |
| Swagger Tag | defenseAreaApi                   |
| 作用说明    | 批量撤防                         |

**请求参数（Body）：**

| 字段             | 类型             | 说明 |
| ---------------- | ---------------- | ---- |
| `defenceAreaId`  | `integer`        |      |
| `deviceCode`     | `string`         |      |
| `modelType`      | `integer`        |      |
| `defenceCycle`   | `string`         |      |
| `username`       | `string`         |      |
| `defenceStatus`  | `integer`        |      |
| `onlineStatus`   | `integer`        |      |
| `defenceAreaIds` | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.6 全部布防

| 项          | 内容                          |
| ----------- | ----------------------------- |
| 接口路径    | `/defenceArea/defenceAll`     |
| 请求方法    | `POST`                        |
| 前端封装    | `SystemController.defenceAll` |
| Swagger Tag | defenseAreaApi                |
| 作用说明    | 全部布防                      |

**请求参数（Body）：**

| 字段           | 类型            | 说明 |
| -------------- | --------------- | ---- |
| `id`           | `integer`       |      |
| `deviceCode`   | `string`        |      |
| `deviceCodes`  | `array<string>` |      |
| `defenceCycle` | `string`        |      |
| `modelType`    | `integer`       |      |
| `username`     | `string`        |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.7 全部撤防

| 项          | 内容                           |
| ----------- | ------------------------------ |
| 接口路径    | `/defenceArea/withdrawAll`     |
| 请求方法    | `POST`                         |
| 前端封装    | `SystemController.withdrawAll` |
| Swagger Tag | defenseAreaApi                 |
| 作用说明    | 全部撤防                       |

**请求参数（Body）：**

| 字段           | 类型            | 说明 |
| -------------- | --------------- | ---- |
| `id`           | `integer`       |      |
| `deviceCode`   | `string`        |      |
| `deviceCodes`  | `array<string>` |      |
| `defenceCycle` | `string`        |      |
| `modelType`    | `integer`       |      |
| `username`     | `string`        |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.8 布防周期设定

| 项          | 内容                            |
| ----------- | ------------------------------- |
| 接口路径    | `/defenceArea/defenceCycle`     |
| 请求方法    | `POST`                          |
| 前端封装    | `SystemController.defenceCycle` |
| Swagger Tag | defenseAreaApi                  |
| 作用说明    | 布防周期设定                    |

**请求参数（Body）：**

| 字段             | 类型             | 说明 |
| ---------------- | ---------------- | ---- |
| `defenceAreaId`  | `integer`        |      |
| `deviceCode`     | `string`         |      |
| `modelType`      | `integer`        |      |
| `defenceCycle`   | `string`         |      |
| `username`       | `string`         |      |
| `defenceStatus`  | `integer`        |      |
| `onlineStatus`   | `integer`        |      |
| `defenceAreaIds` | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.9 获取驱动缓存的防区状态

| 项          | 内容                                      |
| ----------- | ----------------------------------------- |
| 接口路径    | `/defenceArea/getDriverDefenceStatus`     |
| 请求方法    | `POST`                                    |
| 前端封装    | `SystemController.getDriverDefenceStatus` |
| Swagger Tag | defenseAreaApi                            |
| 作用说明    | 获取驱动缓存的防区状态                    |

**请求参数（Body）：**

| 字段              | 类型      | 说明                                           |
| ----------------- | --------- | ---------------------------------------------- |
| `gdn`             | `string`  | 网关编码                                       |
| `dn`              | `string`  | 设备编码                                       |
| `action`          | `string`  | 更新操作                                       |
| `type`            | `integer` | 1-设备挂载在数采设备下; 2-设备挂载在通信网关下 |
| `collectServerId` | `integer` | 数采id                                         |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `integer` |      |

---
