# 资料管理（material_management）知识库

> 上级模块索引：[tool_information.md](./tool_information.md) · 总索引：[README.md](./README.md) · 页面总表：[TOTAL-MODULE.md](./TOTAL-MODULE.md)

## 0. 路由与归属信息

| 项                 | 内容                                                                                     |
| ------------------ | ---------------------------------------------------------------------------------------- |
| 模块名称（中文）   | 资料管理                                                                                 |
| 模块名称（英文）   | Material Management                                                                      |
| 所属 Group（中文） | 工具资料                                                                                 |
| 所属 Group（英文） | Tools and Materials                                                                      |
| Group ID           | `tool_information`                                                                       |
| 菜单位置           | 配置管理平台 → 阵地维护管理 → 工具资料 → 资料管理                                        |
| 路由路径           | `/config_management/positional_management/material_management`                           |
| 页面目录           | `src/pages/config_management/positional_management/tool_information/material_management` |

## 1. 模块定位与项目作用

物资管理是综合信息平台中「工具资料」业务域下的功能模块，对应页面目录 `src/pages/config_management/positional_management/tool_information/material_management`。

在项目中的主要作用：

- 作为「配置管理平台 → 阵地维护管理 → 工具资料 → 物资管理」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
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

| 字段名           | 中文含义 | 作用说明                        |
| ---------------- | -------- | ------------------------------- |
| name             | 资料名称 | 模块表单/列表字段，详见页面配置 |
| code             | 资料编码 | 模块表单/列表字段，详见页面配置 |
| categoryTypeName | 资料类型 | 模块表单/列表字段，详见页面配置 |
| fileLevel        | 密级     | 模块表单/列表字段，详见页面配置 |
| fileUnit         | 单位     | 模块表单/列表字段，详见页面配置 |
| fileNum          | 数量     | 模块表单/列表字段，详见页面配置 |
| fileMakeUnit     | 编制单位 | 模块表单/列表字段，详见页面配置 |
| saveTime         | 存档时间 | 模块表单/列表字段，详见页面配置 |
| savePosition     | 存放位置 | 模块表单/列表字段，详见页面配置 |
| remark           | 备注     | 模块表单/列表字段，详见页面配置 |
| attachments      | 资料附件 | 模块表单/列表字段，详见页面配置 |
| file             | file     | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

- 新建/新增
- 编辑
- 详情回填
- 导出
- 导入
- 左侧树筛选
- 启用/停用

---

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                                    | 关系说明                                     |
| ------------------------------------------- | -------------------------------------------- |
| 入库存管理（in_stock_management）           | 同级功能模块，可共同构成「工具资料」业务能力 |
| 仓储位置管理（storage_position_management） | 同级功能模块，可共同构成「工具资料」业务能力 |
| 工具管理（tool_management）                 | 同级功能模块，可共同构成「工具资料」业务能力 |
| 工具类型管理（tool_type_management）        | 同级功能模块，可共同构成「工具资料」业务能力 |

### 5.2 上游依赖 / 下游消费

- **上游**：根据本页接口与字段引用，上游主要为：用户及参数管理（`user`）。另可能依赖登录会话与菜单授权（用户及参数管理）。
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

本模块（`material_management`）位于 `src/pages/config_management/positional_management/tool_information/material_management`，归属「工具资料」。它负责「物资管理」相关业务的页面交互与数据读写。维护本模块时，请同步关注接口契约、字段语义及与兄弟模块的数据一致性。

---

## 8. 接口清单

以下接口由本模块页面代码直接或通过 `@/services` Controller 调用，参数与响应 Schema 来自平台 OpenAPI（若可匹配）。

### 8.1 获取文件列表

| 项          | 内容                                       |
| ----------- | ------------------------------------------ |
| 接口路径    | `/misFile/getMisFileList`                  |
| 请求方法    | `POST`                                     |
| 前端封装    | `ToolManagementController.getMaterialList` |
| Swagger Tag | facilityFileApi                            |
| 作用说明    | 获取文件列表                               |

**请求参数（Body）：**

| 字段             | 类型      | 说明 |
| ---------------- | --------- | ---- |
| `page`           | `integer` |      |
| `size`           | `integer` |      |
| `fileName`       | `string`  |      |
| `fileCategoryId` | `integer` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.2 修改文件

| 项          | 内容                                      |
| ----------- | ----------------------------------------- |
| 接口路径    | `/misFile/editMisFile`                    |
| 请求方法    | `POST`                                    |
| 前端封装    | `ToolManagementController.updateMaterial` |
| Swagger Tag | facilityFileApi                           |
| 作用说明    | 修改文件                                  |

**请求参数（Body）：**

| 字段             | 类型      | 说明 |
| ---------------- | --------- | ---- |
| `id`             | `integer` |      |
| `fileCode`       | `string`  |      |
| `fileName`       | `string`  |      |
| `fileCategoryId` | `integer` |      |
| `fileLevel`      | `integer` |      |
| `fileUrl`        | `string`  |      |
| `fileUnit`       | `string`  |      |
| `fileMakeUnit`   | `string`  |      |
| `fileNum`        | `integer` |      |
| `saveTime`       | `string`  |      |
| `savePosition`   | `string`  |      |
| `remark`         | `string`  |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.3 添加文件

| 项          | 内容                                   |
| ----------- | -------------------------------------- |
| 接口路径    | `/misFile/addMisFile`                  |
| 请求方法    | `POST`                                 |
| 前端封装    | `ToolManagementController.addMaterial` |
| Swagger Tag | facilityFileApi                        |
| 作用说明    | 添加文件                               |

**请求参数（Body）：**

| 字段             | 类型      | 说明 |
| ---------------- | --------- | ---- |
| `fileCode`       | `string`  |      |
| `fileName`       | `string`  |      |
| `fileCategoryId` | `integer` |      |
| `fileLevel`      | `integer` |      |
| `fileUrl`        | `string`  |      |
| `fileUnit`       | `string`  |      |
| `fileMakeUnit`   | `string`  |      |
| `fileNum`        | `integer` |      |
| `saveTime`       | `string`  |      |
| `savePosition`   | `string`  |      |
| `remark`         | `string`  |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.4 删除文件

| 项          | 内容                                      |
| ----------- | ----------------------------------------- |
| 接口路径    | `/misFile/delMisFile`                     |
| 请求方法    | `POST`                                    |
| 前端封装    | `ToolManagementController.deleteMaterial` |
| Swagger Tag | facilityFileApi                           |
| 作用说明    | 删除文件                                  |

**请求参数（Body）：**

| 字段 | 类型      | 说明 |
| ---- | --------- | ---- |
| `id` | `integer` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.5 获取存放位置数组

| 项          | 内容                                                  |
| ----------- | ----------------------------------------------------- |
| 接口路径    | `/misStoragePosition/getMisStoragePositionArray`      |
| 请求方法    | `POST`                                                |
| 前端封装    | `ToolManagementController.getMisStoragePositionArray` |
| Swagger Tag | facilityStoragePositionApi                            |
| 作用说明    | 获取存放位置数组                                      |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.6 获取文件分类树

| 项          | 内容                                               |
| ----------- | -------------------------------------------------- |
| 接口路径    | `/misFileCategory/getMisFileCategoryTree`          |
| 请求方法    | `POST`                                             |
| 前端封装    | `ToolManagementController.getMaterialCategoryTree` |
| Swagger Tag | facilityFileCategoryApi                            |
| 作用说明    | 获取文件分类树                                     |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.7 修改文件分类

| 项          | 内容                                              |
| ----------- | ------------------------------------------------- |
| 接口路径    | `/misFileCategory/editMisFileCategory`            |
| 请求方法    | `POST`                                            |
| 前端封装    | `ToolManagementController.updateMaterialCategory` |
| Swagger Tag | facilityFileCategoryApi                           |
| 作用说明    | 修改文件分类                                      |

**请求参数（Body）：**

| 字段           | 类型      | 说明 |
| -------------- | --------- | ---- |
| `id`           | `integer` |      |
| `categoryCode` | `string`  |      |
| `categoryName` | `string`  |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.8 添加文件分类

| 项          | 内容                                           |
| ----------- | ---------------------------------------------- |
| 接口路径    | `/misFileCategory/addMisFileCategory`          |
| 请求方法    | `POST`                                         |
| 前端封装    | `ToolManagementController.addMaterialCategory` |
| Swagger Tag | facilityFileCategoryApi                        |
| 作用说明    | 添加文件分类                                   |

**请求参数（Body）：**

| 字段           | 类型      | 说明 |
| -------------- | --------- | ---- |
| `categoryCode` | `string`  |      |
| `categoryName` | `string`  |      |
| `pid`          | `integer` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.9 删除文件分类

| 项          | 内容                                              |
| ----------- | ------------------------------------------------- |
| 接口路径    | `/misFileCategory/delMisFileCategory`             |
| 请求方法    | `POST`                                            |
| 前端封装    | `ToolManagementController.deleteMaterialCategory` |
| Swagger Tag | facilityFileCategoryApi                           |
| 作用说明    | 删除文件分类                                      |

**请求参数（Body）：**

| 字段 | 类型      | 说明 |
| ---- | --------- | ---- |
| `id` | `integer` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---
