# 统计（statistics）知识库

## 0. 路由与归属信息

| 项                 | 内容                   |
| ------------------ | ---------------------- |
| 模块名称（中文）   | 统计                   |
| 模块名称（英文）   | Statistics             |
| 所属 Group（中文） | 统计                   |
| 所属 Group（英文） | Statistics             |
| Group ID           | `statistics`           |
| 菜单位置           | 统计                   |
| 路由路径           | `/statistics`          |
| 页面目录           | `src/pages/statistics` |

## 1. 模块定位与项目作用

统计是综合信息平台中「统计」业务域下的功能模块，对应页面目录 `src/pages/statistics`。

在项目中的主要作用：

- 作为「统计」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
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

## 3. 功能清单

- 导出
- 导入

---

## 4. 与其他功能模块的关系

### 4.1 相关统计与数据源

| 关联模块         | 文档                                                     | 关系说明               |
| ---------------- | -------------------------------------------------------- | ---------------------- |
| 门禁统计         | [door_statistics.md](./door_statistics.md)               | 门禁维度统计展示       |
| 库房统计         | [storage_statistics.md](./storage_statistics.md)         | 库房维度统计展示       |
| 报警查询统计     | [alarm_query_statistics.md](./alarm_query_statistics.md) | 配置侧报警统计能力     |
| 历史数据查询统计 | [history_data.md](./history_data.md)                     | 历史趋势与统计         |
| 总览             | [overview.md](./overview.md)                             | 门户入口，可导航至统计 |

### 4.2 上游依赖 / 下游消费

- **上游**：根据本页接口与字段引用，上游主要为：用户及参数管理（`user`）、监控设备（`monitor_equipment`）、设备变量（`device_variable`）。另可能依赖登录会话与菜单授权（用户及参数管理）。
- **下游**：供值班指挥与运维决策查看，一般不回写业务主数据。

## 5. 关键业务规则与注意事项

1. 操作前确认当前用户具备对应菜单与按钮权限。
2. 删除、导入、批量变更等操作可能影响下游运行态数据，执行前应确认范围。
3. 若模块涉及驱动/采集类配置，变更后可能需要在数采或相关服务侧刷新配置后生效。
4. 接口入参以 Swagger 与前端封装为准，注意必填项与枚举值。
5. 国际化环境下，界面文案以 `src/locales` 配置为准。

---

## 6. 总结

本模块（`statistics`）位于 `src/pages/statistics`，归属「统计」。它负责「统计」相关业务的页面交互与数据读写。维护本模块时，请同步关注接口契约、字段语义及与兄弟模块的数据一致性。

---

## 7. 接口清单

以下接口由本模块页面代码直接或通过 `@/services` Controller 调用，参数与响应 Schema 来自平台 OpenAPI（若可匹配）。

### 7.1 报警统计

| 项          | 内容                              |
| ----------- | --------------------------------- |
| 接口路径    | `/devops/getAlarmStatic`          |
| 请求方法    | `POST`                            |
| 前端封装    | `SystemController.getAlarmStatic` |
| Swagger Tag | devopsApi                         |
| 作用说明    | 报警统计                          |

**请求参数（Body）：**

| 字段                | 类型      | 说明                                     |
| ------------------- | --------- | ---------------------------------------- |
| `subSystemId`       | `integer` |                                          |
| `deviceId`          | `integer` |                                          |
| `deviceVarId`       | `integer` |                                          |
| `startTime`         | `string`  |                                          |
| `endTime`           | `string`  |                                          |
| `statisticsCycleId` | `integer` | @NotNull(message = "统计周期ID不能为空") |
| `statisticsWayId`   | `integer` | @NotNull(message = "统计方式ID不能为空") |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `key`     | `object`  |      |
| `key.key` | `integer` |      |

---

### 7.2 故障统计

| 项          | 内容                              |
| ----------- | --------------------------------- |
| 接口路径    | `/devops/getFaultStatic`          |
| 请求方法    | `POST`                            |
| 前端封装    | `SystemController.getFaultStatic` |
| Swagger Tag | devopsApi                         |
| 作用说明    | 故障统计                          |

**请求参数（Body）：**

| 字段          | 类型      | 说明 |
| ------------- | --------- | ---- |
| `subSystemId` | `integer` |      |

**响应体：**

| 字段  | 类型      | 说明 |
| ----- | --------- | ---- |
| `key` | `integer` |      |

---

### 7.3 设备统计

| 项          | 内容                            |
| ----------- | ------------------------------- |
| 接口路径    | `/devops/getDevStatic`          |
| 请求方法    | `POST`                          |
| 前端封装    | `SystemController.getDevStatic` |
| Swagger Tag | devopsApi                       |
| 作用说明    | 设备统计                        |

**请求参数（Body）：**

| 字段          | 类型      | 说明 |
| ------------- | --------- | ---- |
| `subSystemId` | `integer` |      |

**响应体：**

| 字段         | 类型      | 说明 |
| ------------ | --------- | ---- |
| `totalNum`   | `integer` |      |
| `onlineNum`  | `integer` |      |
| `offlineNum` | `integer` |      |
| `enableNum`  | `integer` |      |
| `disableNum` | `integer` |      |

---
