# 撤布防记录（evacuation_record）知识库

> 上级模块索引：[perimeter_setting.md](./perimeter_setting.md) · 总索引：[README.md](./README.md) · 页面总表：[TOTAL-MODULE.md](./TOTAL-MODULE.md)

## 0. 路由与归属信息

| 项                 | 内容                                                                     |
| ------------------ | ------------------------------------------------------------------------ |
| 模块名称（中文）   | 撤布防记录                                                               |
| 模块名称（英文）   | Evacuation Record                                                        |
| 所属 Group（中文） | 周界防区设定                                                             |
| 所属 Group（英文） | Perimeter Zone Setting                                                   |
| Group ID           | `perimeter_setting`                                                      |
| 菜单位置           | 配置管理平台 → 配置管理 → 周界防区设定 → 撤布防记录                      |
| 路由路径           | `/config_management/config/evacuation_record`                            |
| 页面目录           | `src/pages/config_management/config/perimeter_setting/evacuation_record` |

## 1. 模块定位与项目作用

撤防记录是综合信息平台中「周界防区设定」业务域下的功能模块，对应页面目录 `src/pages/config_management/config/perimeter_setting/evacuation_record`。

在项目中的主要作用：

- 作为「配置管理平台 → 配置管理 → 周界防区设定 → 撤防记录」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
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
| areaId           | 防区名称     | 模块表单/列表字段，详见页面配置 |
| gatewayName      | 网关编号     | 模块表单/列表字段，详见页面配置 |
| gdn              | 更新前状态   | 模块表单/列表字段，详见页面配置 |
| beforeStatusName | 更新后状态   | 模块表单/列表字段，详见页面配置 |
| afterStatusName  | 更新时间     | 模块表单/列表字段，详见页面配置 |
| areaName         | 防区名称     | 模块表单/列表字段，详见页面配置 |
| deviceName       | 防区设备名称 | 模块表单/列表字段，详见页面配置 |
| dn               | 防区设备编号 | 模块表单/列表字段，详见页面配置 |
| createdTime      | 更新时间     | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

- 导出
- 导入

---

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                            | 关系说明                                         |
| ----------------------------------- | ------------------------------------------------ |
| 防区分组（group）                   | 同级功能模块，可共同构成「周界防区设定」业务能力 |
| 维护（maintenance）                 | 同级功能模块，可共同构成「周界防区设定」业务能力 |
| 手动周期撤防（manual_cycle_disarm） | 同级功能模块，可共同构成「周界防区设定」业务能力 |

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

本模块（`evacuation_record`）位于 `src/pages/config_management/config/perimeter_setting/evacuation_record`，归属「周界防区设定」。它负责「撤防记录」相关业务的页面交互与数据读写。维护本模块时，请同步关注接口契约、字段语义及与兄弟模块的数据一致性。

---

## 8. 接口清单

以下接口由本模块页面代码直接或通过 `@/services` Controller 调用，参数与响应 Schema 来自平台 OpenAPI（若可匹配）。

### 8.1 获取防区撤布防状态变更历史记录

| 项          | 内容                                 |
| ----------- | ------------------------------------ |
| 接口路径    | `/defenceArea/getDefenceRecords`     |
| 请求方法    | `POST`                               |
| 前端封装    | `SystemController.getDefenceRecords` |
| Swagger Tag | defenseAreaApi                       |
| 作用说明    | 获取防区撤布防状态变更历史记录       |

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
| `areaId`         | `integer`       |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.2 获取全部防区

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
