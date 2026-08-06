# 专业（major）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                 |
| ------------------ | ---------------------------------------------------- |
| 模块名称（中文）   | 专业                                                 |
| 模块名称（英文）   | Major                                                |
| 所属 Group（中文） | 字典表                                               |
| 所属 Group（英文） | Dictionary Table                                     |
| Group ID           | `dic_table`                                          |
| 菜单位置           | 配置管理平台 → 系统管理 → 字典表 → 专业              |
| 路由路径           | `/config_management/system/dic_table/major`          |
| 页面目录           | `src/pages/config_management/system/dic_table/major` |

## 1. 模块定位与项目作用

专业是综合信息平台中「字典表」业务域下的功能模块，对应页面目录 `src/pages/config_management/system/dic_table/major`。

在项目中的主要作用：

- 作为「配置管理平台 → 系统管理 → 字典表 → 专业」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
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
| id     | 名称     | 模块表单/列表字段，详见页面配置 |
| name   | 名称     | 模块表单/列表字段，详见页面配置 |
| remark | 备注     | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

- 新建/新增
- 编辑
- 删除
- 详情回填
- 导出
- 导入

---

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                           | 关系说明                                   |
| ---------------------------------- | ------------------------------------------ |
| 告警分类（alarm_category）         | 同级功能模块，可共同构成「字典表」业务能力 |
| 告警等级（alarm_level）            | 同级功能模块，可共同构成「字典表」业务能力 |
| 告警来源（alarm_source）           | 同级功能模块，可共同构成「字典表」业务能力 |
| 信息发布状态（info_release_state） | 同级功能模块，可共同构成「字典表」业务能力 |
| 岗位（job）                        | 同级功能模块，可共同构成「字典表」业务能力 |
| 军衔等级（military_rank）          | 同级功能模块，可共同构成「字典表」业务能力 |
| 民族（nationality）                | 同级功能模块，可共同构成「字典表」业务能力 |
| 对象类别（object_class）           | 同级功能模块，可共同构成「字典表」业务能力 |
| 技能（skill）                      | 同级功能模块，可共同构成「字典表」业务能力 |
| 风向方向（wind_direction）         | 同级功能模块，可共同构成「字典表」业务能力 |

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

本模块（`major`）位于 `src/pages/config_management/system/dic_table/major`，归属「字典表」。它负责「专业」相关业务的页面交互与数据读写。维护本模块时，请同步关注接口契约、字段语义及与兄弟模块的数据一致性。

---

## 8. 接口清单

以下接口由本模块页面代码直接或通过 `@/services` Controller 调用，参数与响应 Schema 来自 `swaggerApi.json`（若可匹配）。

### 8.1 获取专业列表

| 项          | 内容                               |
| ----------- | ---------------------------------- |
| 接口路径    | `/dic/getMajorList`                |
| 请求方法    | `POST`                             |
| 前端封装    | `SystemController.getMajorDicPage` |
| Swagger Tag | dictionaryApi                      |
| 作用说明    | 获取专业列表                       |

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

### 8.2 exportMajorDic

| 项       | 内容                              |
| -------- | --------------------------------- |
| 接口路径 | `/dic/exportMajor`                |
| 请求方法 | `GET`                             |
| 前端封装 | `SystemController.exportMajorDic` |
| 作用说明 | 见模块业务逻辑                    |

_未在 `swaggerApi.json` 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---

### 8.3 新增专业

| 项          | 内容                           |
| ----------- | ------------------------------ |
| 接口路径    | `/dic/addMajor`                |
| 请求方法    | `POST`                         |
| 前端封装    | `SystemController.addMajorDic` |
| Swagger Tag | dictionaryApi                  |
| 作用说明    | 新增专业                       |

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

### 8.4 获取专业详情

| 项          | 内容                               |
| ----------- | ---------------------------------- |
| 接口路径    | `/dic/getMajorById`                |
| 请求方法    | `POST`                             |
| 前端封装    | `SystemController.getMajorDicById` |
| Swagger Tag | dictionaryApi                      |
| 作用说明    | 获取专业详情                       |

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

| 字段               | 类型      | 说明 |
| ------------------ | --------- | ---- |
| `code`             | `integer` |      |
| `message`          | `string`  |      |
| `data`             | `object`  |      |
| `data.id`          | `integer` |      |
| `data.name`        | `string`  |      |
| `data.createdTime` | `string`  |      |
| `data.updatedTime` | `string`  |      |

---

### 8.5 更新专业

| 项          | 内容                              |
| ----------- | --------------------------------- |
| 接口路径    | `/dic/updateMajor`                |
| 请求方法    | `POST`                            |
| 前端封装    | `SystemController.updateMajorDic` |
| Swagger Tag | dictionaryApi                     |
| 作用说明    | 更新专业                          |

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

### 8.6 删除专业

| 项          | 内容                              |
| ----------- | --------------------------------- |
| 接口路径    | `/dic/deleteMajor`                |
| 请求方法    | `POST`                            |
| 前端封装    | `SystemController.deleteMajorDic` |
| Swagger Tag | dictionaryApi                     |
| 作用说明    | 删除专业                          |

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
