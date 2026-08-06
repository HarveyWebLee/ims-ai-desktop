# 保养任务管理（maintenance_task_management）知识库

> 上级模块索引：[maintenance_management.md](./maintenance_management.md) · 总索引：[README.md](./README.md) · 页面总表：[TOTAL-MODULE.md](./TOTAL-MODULE.md)

## 0. 路由与归属信息

| 项                 | 内容                                                                                                   |
| ------------------ | ------------------------------------------------------------------------------------------------------ |
| 模块名称（中文）   | 保养任务管理                                                                                           |
| 模块名称（英文）   | Maintenance Task Management                                                                            |
| 所属 Group（中文） | 维护保养管理                                                                                           |
| 所属 Group（英文） | Maintenance Management                                                                                 |
| Group ID           | `maintenance_management`                                                                               |
| 菜单位置           | 配置管理平台 → 阵地维护管理 → 维护保养管理 → 保养任务管理                                              |
| 路由路径           | `/config_management/positional_management/maintenance_task_management`                                 |
| 页面目录           | `src/pages/config_management/positional_management/maintenance_management/maintenance_task_management` |

## 1. 模块定位与项目作用

保养任务管理是综合信息平台中「维护保养管理」业务域下的功能模块，对应页面目录 `src/pages/config_management/positional_management/maintenance_management/maintenance_task_management`。

在项目中的主要作用：

- 作为「配置管理平台 → 阵地维护管理 → 维护保养管理 → 保养任务管理」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
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

| 字段名            | 中文含义     | 作用说明                        |
| ----------------- | ------------ | ------------------------------- |
| sceneName         | 保养方案     | 模块表单/列表字段，详见页面配置 |
| startTime         | 结束时间     | 模块表单/列表字段，详见页面配置 |
| deviceName        | 编号         | 模块表单/列表字段，详见页面配置 |
| startTimeRange    | 开始时间范围 | 模块表单/列表字段，详见页面配置 |
| sceneId           | 保养方案     | 模块表单/列表字段，详见页面配置 |
| timeRange         | 起止时间     | 模块表单/列表字段，详见页面配置 |
| taskManager       | 负责人       | 模块表单/列表字段，详见页面配置 |
| taskSigner        | 签发人       | 模块表单/列表字段，详见页面配置 |
| endTime           | 结束时间     | 模块表单/列表字段，详见页面配置 |
| taskParticipant   | 参加人       | 模块表单/列表字段，详见页面配置 |
| problemHandle     | 问题处理     | 模块表单/列表字段，详见页面配置 |
| dutyChange        | 责任变更     | 模块表单/列表字段，详见页面配置 |
| materialConsume   | 材料消耗     | 模块表单/列表字段，详见页面配置 |
| deviceCode        | 编号         | 模块表单/列表字段，详见页面配置 |
| deviceCategoryId  | 设备类别     | 模块表单/列表字段，详见页面配置 |
| unitCode          | 隶属单位     | 模块表单/列表字段，详见页面配置 |
| installPositionId | 安装部位     | 模块表单/列表字段，详见页面配置 |
| deviceCodes       | 保养设备     | 模块表单/列表字段，详见页面配置 |
| taskStatus        | taskStatus   | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

- 导出
- 导入
- 左侧树筛选
- 启用/停用
- 分页查询

---

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                                                  | 关系说明                                         |
| --------------------------------------------------------- | ------------------------------------------------ |
| maintenance需求管理（maintenance_requirement_management） | 同级功能模块，可共同构成「维护保养管理」业务能力 |
| maintenance方案管理（maintenance_scheme_management）      | 同级功能模块，可共同构成「维护保养管理」业务能力 |

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

本模块（`maintenance_task_management`）位于 `src/pages/config_management/positional_management/maintenance_management/maintenance_task_management`，归属「维护保养管理」。它负责「保养任务管理」相关业务的页面交互与数据读写。维护本模块时，请同步关注接口契约、字段语义及与兄弟模块的数据一致性。

---

## 8. 接口清单

以下接口由本模块页面代码直接或通过 `@/services` Controller 调用，参数与响应 Schema 来自平台 OpenAPI（若可匹配）。

### 8.1 获取任务详情

| 项          | 内容                                            |
| ----------- | ----------------------------------------------- |
| 接口路径    | `/misUpkeepTask/getMisUpkeepTaskInfoList`       |
| 请求方法    | `POST`                                          |
| 前端封装    | `PositionalManagement.getMisUpkeepTaskInfoList` |
| Swagger Tag | facilityUpkeepTaskApi                           |
| 作用说明    | 获取任务详情                                    |

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

### 8.2 记录保养和状态

| 项          | 内容                                         |
| ----------- | -------------------------------------------- |
| 接口路径    | `/misUpkeepTask/editMisUpkeepTaskInfo`       |
| 请求方法    | `POST`                                       |
| 前端封装    | `PositionalManagement.editMisUpkeepTaskInfo` |
| Swagger Tag | facilityUpkeepTaskApi                        |
| 作用说明    | 记录保养和状态                               |

**请求参数（Body）：**

| 字段           | 类型      | 说明 |
| -------------- | --------- | ---- |
| `id`           | `string`  |      |
| `upkeepStatus` | `integer` |      |
| `upkeepRecord` | `string`  |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.3 editMisUpkeepRecord

| 项       | 内容                                       |
| -------- | ------------------------------------------ |
| 接口路径 | `/misUpkeepTask/editMisUpkeepRecord`       |
| 请求方法 | `POST`                                     |
| 前端封装 | `PositionalManagement.editMisUpkeepRecord` |
| 作用说明 | 见模块业务逻辑                             |

_未在平台 OpenAPI 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---

### 8.4 getMisUpkeepScenes

| 项       | 内容                                      |
| -------- | ----------------------------------------- |
| 接口路径 | `/misUpkeepScene/getMisUpkeepScenes`      |
| 请求方法 | `POST`                                    |
| 前端封装 | `PositionalManagement.getMisUpkeepScenes` |
| 作用说明 | 见模块业务逻辑                            |

_未在平台 OpenAPI 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---

### 8.5 获取阵地人员列表

| 项          | 内容                                     |
| ----------- | ---------------------------------------- |
| 接口路径    | `/positionPerson/getPositionPersonList`  |
| 请求方法    | `POST`                                   |
| 前端封装    | `SystemController.getPositionPersonList` |
| Swagger Tag | positionPersonnelApi                     |
| 作用说明    | 获取阵地人员列表                         |

**请求参数（Body）：**

| 字段           | 类型             | 说明 |
| -------------- | ---------------- | ---- |
| `id`           | `integer`        |      |
| `personName`   | `string`         |      |
| `militaryName` | `string`         |      |
| `profession`   | `string`         |      |
| `major`        | `string`         |      |
| `skillLevel`   | `string`         |      |
| `ids`          | `array<integer>` |      |

**响应体：**

| 字段                  | 类型            | 说明 |
| --------------------- | --------------- | ---- |
| `code`                | `integer`       |      |
| `message`             | `string`        |      |
| `data`                | `array<object>` |      |
| `data[].id`           | `integer`       |      |
| `data[].personName`   | `string`        |      |
| `data[].militaryName` | `string`        |      |
| `data[].profession`   | `string`        |      |
| `data[].major`        | `string`        |      |
| `data[].skillLevel`   | `string`        |      |
| `data[].createdTime`  | `string`        |      |
| `data[].updatedTime`  | `string`        |      |

---

### 8.6 获取设施设备分类列表

| 项          | 内容                                              |
| ----------- | ------------------------------------------------- |
| 接口路径    | `/misFacilityCategory/getMisFacilityCategoryTree` |
| 请求方法    | `POST`                                            |
| 前端封装    | `PositionalManagement.getMiFacilityCategoryTree`  |
| Swagger Tag | facilityCategoryApi                               |
| 作用说明    | 获取设施设备分类列表                              |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.7 获取安装部位数组

| 项          | 内容                                           |
| ----------- | ---------------------------------------------- |
| 接口路径    | `/misFacilityPosition/getMisFacilityPositions` |
| 请求方法    | `POST`                                         |
| 前端封装    | `PositionalManagement.getMisFacilityPositions` |
| Swagger Tag | facilityPositionApi                            |
| 作用说明    | 获取安装部位数组                               |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.8 获取方案所有设备列表

| 项          | 内容                                      |
| ----------- | ----------------------------------------- |
| 接口路径    | `/misUpkeepScene/getSceneDeviceList`      |
| 请求方法    | `POST`                                    |
| 前端封装    | `PositionalManagement.getSceneDeviceList` |
| Swagger Tag | facilityUpkeepSceneApi                    |
| 作用说明    | 获取方案所有设备列表                      |

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

### 8.9 获取任务

| 项          | 内容                                    |
| ----------- | --------------------------------------- |
| 接口路径    | `/misUpkeepTask/getMisUpkeepTask`       |
| 请求方法    | `POST`                                  |
| 前端封装    | `PositionalManagement.getMisUpkeepTask` |
| Swagger Tag | facilityUpkeepTaskApi                   |
| 作用说明    | 获取任务                                |

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

### 8.10 修改任务状态

| 项          | 内容                                           |
| ----------- | ---------------------------------------------- |
| 接口路径    | `/misUpkeepTask/editMisUpkeepTaskStatus`       |
| 请求方法    | `POST`                                         |
| 前端封装    | `PositionalManagement.editMisUpkeepTaskStatus` |
| Swagger Tag | facilityUpkeepTaskApi                          |
| 作用说明    | 修改任务状态                                   |

**请求参数（Body）：**

| 字段         | 类型      | 说明 |
| ------------ | --------- | ---- |
| `id`         | `integer` |      |
| `taskStatus` | `integer` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.11 获取任务列表

| 项          | 内容                                        |
| ----------- | ------------------------------------------- |
| 接口路径    | `/misUpkeepTask/getMisUpkeepTaskList`       |
| 请求方法    | `POST`                                      |
| 前端封装    | `PositionalManagement.getMisUpkeepTaskList` |
| Swagger Tag | facilityUpkeepTaskApi                       |
| 作用说明    | 获取任务列表                                |

**请求参数（Body）：**

| 字段          | 类型      | 说明 |
| ------------- | --------- | ---- |
| `page`        | `integer` |      |
| `size`        | `integer` |      |
| `startTime`   | `string`  |      |
| `endTime`     | `string`  |      |
| `taskStatus`  | `integer` |      |
| `taskManager` | `string`  |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.12 添加任务

| 项          | 内容                                    |
| ----------- | --------------------------------------- |
| 接口路径    | `/misUpkeepTask/addMisUpkeepTask`       |
| 请求方法    | `POST`                                  |
| 前端封装    | `PositionalManagement.addMisUpkeepTask` |
| Swagger Tag | facilityUpkeepTaskApi                   |
| 作用说明    | 添加任务                                |

**请求参数（Body）：**

| 字段              | 类型            | 说明 |
| ----------------- | --------------- | ---- |
| `sceneId`         | `integer`       |      |
| `taskManager`     | `string`        |      |
| `taskSigner`      | `string`        |      |
| `taskParticipant` | `string`        |      |
| `startTime`       | `string`        |      |
| `endTime`         | `string`        |      |
| `problemHandle`   | `string`        |      |
| `dutyChange`      | `string`        |      |
| `materialConsume` | `string`        |      |
| `deviceCodes`     | `array<string>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.13 修改任务

| 项          | 内容                                     |
| ----------- | ---------------------------------------- |
| 接口路径    | `/misUpkeepTask/editMisUpkeepTask`       |
| 请求方法    | `POST`                                   |
| 前端封装    | `PositionalManagement.editMisUpkeepTask` |
| Swagger Tag | facilityUpkeepTaskApi                    |
| 作用说明    | 修改任务                                 |

**请求参数（Body）：**

| 字段              | 类型            | 说明 |
| ----------------- | --------------- | ---- |
| `id`              | `integer`       |      |
| `sceneId`         | `integer`       |      |
| `taskManager`     | `string`        |      |
| `taskSigner`      | `string`        |      |
| `taskParticipant` | `string`        |      |
| `startTime`       | `string`        |      |
| `endTime`         | `string`        |      |
| `problemHandle`   | `string`        |      |
| `dutyChange`      | `string`        |      |
| `materialConsume` | `string`        |      |
| `deviceCodes`     | `array<string>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.14 删除任务

| 项          | 内容                                    |
| ----------- | --------------------------------------- |
| 接口路径    | `/misUpkeepTask/delMisUpkeepTask`       |
| 请求方法    | `POST`                                  |
| 前端封装    | `PositionalManagement.delMisUpkeepTask` |
| Swagger Tag | facilityUpkeepTaskApi                   |
| 作用说明    | 删除任务                                |

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

### 8.15 获取保养类型数组

| 项          | 内容                                     |
| ----------- | ---------------------------------------- |
| 接口路径    | `/misUpkeepType/getMisUpkeepTypes`       |
| 请求方法    | `POST`                                   |
| 前端封装    | `PositionalManagement.getMisUpkeepTypes` |
| Swagger Tag | facilityUpkeepTypeApi                    |
| 作用说明    | 获取保养类型数组                         |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---
