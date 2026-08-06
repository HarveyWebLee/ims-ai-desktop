# 标签配置（label_config）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                               |
| ------------------ | ------------------------------------------------------------------ |
| 模块名称（中文）   | 标签配置                                                           |
| 模块名称（英文）   | Label Config                                                       |
| 所属 Group（中文） | 标签管理                                                           |
| 所属 Group（英文） | Label Management                                                   |
| Group ID           | `label_management`                                                 |
| 菜单位置           | 配置管理平台 → 配置管理 → 标签管理 → 标签配置                      |
| 路由路径           | `/config_management/config/label_management/label_config`          |
| 页面目录           | `src/pages/config_management/config/label_management/label_config` |

## 1. 模块定位与项目作用

标签配置是综合信息平台中「标签管理」业务域下的功能模块，对应页面目录 `src/pages/config_management/config/label_management/label_config`。

在项目中的主要作用：

- 作为「配置管理平台 → 配置管理 → 标签管理 → 标签配置」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
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

| 字段名      | 中文含义 | 作用说明                        |
| ----------- | -------- | ------------------------------- |
| name        | 标签名称 | 模块表单/列表字段，详见页面配置 |
| labelKey    | 标签键   | 模块表单/列表字段，详见页面配置 |
| labelConfig | 标签配置 | 模块表单/列表字段，详见页面配置 |
| remark      | 描述     | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

- 新建/新增
- 编辑
- 删除
- 详情回填
- 导出
- 导入
- 左侧树筛选

---

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

暂无明显同级兄弟模块，或同级目录未识别为独立页面。

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

本模块（`label_config`）位于 `src/pages/config_management/config/label_management/label_config`，归属「标签管理」。它负责「标签配置」相关业务的页面交互与数据读写。维护本模块时，请同步关注接口契约、字段语义及与兄弟模块的数据一致性。

---

## 8. 接口清单

以下接口由本模块页面代码直接或通过 `@/services` Controller 调用，参数与响应 Schema 来自 `swaggerApi.json`（若可匹配）。

### 8.1 testRedisConnection

| 项       | 内容                                   |
| -------- | -------------------------------------- |
| 接口路径 | `未知`                                 |
| 请求方法 | `未知`                                 |
| 前端封装 | `SystemController.testRedisConnection` |
| 作用说明 | 见模块业务逻辑                         |

_未在 `swaggerApi.json` 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---

### 8.2 获取表名列表

| 项          | 内容                                      |
| ----------- | ----------------------------------------- |
| 接口路径    | `/dataLabelNode/getTableNames`            |
| 请求方法    | `POST`                                    |
| 前端封装    | `DataLabelConfigController.getTableNames` |
| Swagger Tag | dataLabelNodeApi                          |
| 作用说明    | 获取表名列表                              |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

---

### 8.3 获取数据表字段

| 项          | 内容                                       |
| ----------- | ------------------------------------------ |
| 接口路径    | `/dataLabelNode/getTableFields`            |
| 请求方法    | `POST`                                     |
| 前端封装    | `DataLabelConfigController.getTableFields` |
| Swagger Tag | dataLabelNodeApi                           |
| 作用说明    | 获取数据表字段                             |

**请求参数（Body）：**

| 字段        | 类型     | 说明 |
| ----------- | -------- | ---- |
| `tableName` | `string` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.4 getTableColumns

| 项       | 内容                               |
| -------- | ---------------------------------- |
| 接口路径 | `未知`                             |
| 请求方法 | `未知`                             |
| 前端封装 | `SystemController.getTableColumns` |
| 作用说明 | 见模块业务逻辑                     |

_未在 `swaggerApi.json` 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---

### 8.5 获取报警类别字典分页列表

| 项          | 内容                                    |
| ----------- | --------------------------------------- |
| 接口路径    | `/dic/getAlarmCategoryPage`             |
| 请求方法    | `POST`                                  |
| 前端封装    | `SystemController.getAlarmCategoryPage` |
| Swagger Tag | dictionaryApi                           |
| 作用说明    | 获取报警类别字典分页列表                |

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

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.6 添加报警类别

| 项          | 内容                                |
| ----------- | ----------------------------------- |
| 接口路径    | `/dic/addAlarmCategory`             |
| 请求方法    | `POST`                              |
| 前端封装    | `SystemController.addAlarmCategory` |
| Swagger Tag | dictionaryApi                       |
| 作用说明    | 添加报警类别                        |

**请求参数（Body）：**

| 字段                 | 类型             | 说明 |
| -------------------- | ---------------- | ---- |
| `id`                 | `integer`        |      |
| `name`               | `string`         |      |
| `remark`             | `string`         |      |
| `code`               | `string`         |      |
| `parentId`           | `integer`        |      |
| `sort`               | `integer`        |      |
| `ids`                | `array<integer>` |      |
| `alarmLevelStyle`    | `string`         |      |
| `alarmCategoryStyle` | `string`         |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.7 获取报警类别详情

| 项          | 内容                                    |
| ----------- | --------------------------------------- |
| 接口路径    | `/dic/getAlarmCategoryById`             |
| 请求方法    | `POST`                                  |
| 前端封装    | `SystemController.getAlarmCategoryById` |
| Swagger Tag | dictionaryApi                           |
| 作用说明    | 获取报警类别详情                        |

**请求参数（Body）：**

| 字段                 | 类型             | 说明 |
| -------------------- | ---------------- | ---- |
| `id`                 | `integer`        |      |
| `name`               | `string`         |      |
| `remark`             | `string`         |      |
| `code`               | `string`         |      |
| `parentId`           | `integer`        |      |
| `sort`               | `integer`        |      |
| `ids`                | `array<integer>` |      |
| `alarmLevelStyle`    | `string`         |      |
| `alarmCategoryStyle` | `string`         |      |

**响应体：**

| 字段                      | 类型      | 说明         |
| ------------------------- | --------- | ------------ |
| `code`                    | `integer` |              |
| `message`                 | `string`  |              |
| `data`                    | `object`  |              |
| `data.id`                 | `integer` |              |
| `data.alarmCategoryStyle` | `string`  | 全域告警新增 |
| `data.remark`             | `string`  |              |
| `data.createdTime`        | `string`  |              |
| `data.updatedTime`        | `string`  |              |
| `data.name`               | `string`  |              |

---

### 8.8 更新报警类别

| 项          | 内容                                   |
| ----------- | -------------------------------------- |
| 接口路径    | `/dic/updateAlarmCategory`             |
| 请求方法    | `POST`                                 |
| 前端封装    | `SystemController.updateAlarmCategory` |
| Swagger Tag | dictionaryApi                          |
| 作用说明    | 更新报警类别                           |

**请求参数（Body）：**

| 字段                 | 类型             | 说明 |
| -------------------- | ---------------- | ---- |
| `id`                 | `integer`        |      |
| `name`               | `string`         |      |
| `remark`             | `string`         |      |
| `code`               | `string`         |      |
| `parentId`           | `integer`        |      |
| `sort`               | `integer`        |      |
| `ids`                | `array<integer>` |      |
| `alarmLevelStyle`    | `string`         |      |
| `alarmCategoryStyle` | `string`         |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.9 删除报警类别

| 项          | 内容                                   |
| ----------- | -------------------------------------- |
| 接口路径    | `/dic/deleteAlarmCategory`             |
| 请求方法    | `POST`                                 |
| 前端封装    | `SystemController.deleteAlarmCategory` |
| Swagger Tag | dictionaryApi                          |
| 作用说明    | 删除报警类别                           |

**请求参数（Body）：**

| 字段                 | 类型             | 说明 |
| -------------------- | ---------------- | ---- |
| `id`                 | `integer`        |      |
| `name`               | `string`         |      |
| `remark`             | `string`         |      |
| `code`               | `string`         |      |
| `parentId`           | `integer`        |      |
| `sort`               | `integer`        |      |
| `ids`                | `array<integer>` |      |
| `alarmLevelStyle`    | `string`         |      |
| `alarmCategoryStyle` | `string`         |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---
