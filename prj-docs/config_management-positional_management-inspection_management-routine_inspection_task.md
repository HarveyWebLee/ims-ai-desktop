# 巡查任务管理（routine_inspection_task）知识库

> 上级模块索引：[inspection_management.md](./inspection_management.md) · 总索引：[README.md](./README.md) · 页面总表：[TOTAL-MODULE.md](./TOTAL-MODULE.md)

## 0. 路由与归属信息

| 项                 | 内容                                                                                              |
| ------------------ | ------------------------------------------------------------------------------------------------- |
| 模块名称（中文）   | 巡查任务管理                                                                                      |
| 模块名称（英文）   | Routine Inspection Task                                                                           |
| 所属 Group（中文） | 阵地巡检管理                                                                                      |
| 所属 Group（英文） | Position Inspection Management                                                                    |
| Group ID           | `inspection_management`                                                                           |
| 菜单位置           | 配置管理平台 → 阵地维护管理 → 阵地巡检管理 → 巡查任务管理                                         |
| 路由路径           | `/config_management/positional_management/routine_inspection_task`                                |
| 页面目录           | `src/pages/config_management/positional_management/inspection_management/routine_inspection_task` |

## 1. 模块定位与项目作用

例行巡检任务是综合信息平台中「阵地巡检管理」业务域下的功能模块，对应页面目录 `src/pages/config_management/positional_management/inspection_management/routine_inspection_task`。

在项目中的主要作用：

- 作为「配置管理平台 → 阵地维护管理 → 阵地巡检管理 → 例行巡检任务」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
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

| 字段名           | 中文含义                                              | 作用说明                        |
| ---------------- | ----------------------------------------------------- | ------------------------------- |
| taskName         | positional_management.inspection_task.taskName        | 模块表单/列表字段，详见页面配置 |
| startTime        | positional_management.inspection_task.startDate       | 模块表单/列表字段，详见页面配置 |
| endTime          | positional_management.inspection_task.endDate         | 模块表单/列表字段，详见页面配置 |
| taskStatus       | positional_management.inspection_task.taskStatus      | 模块表单/列表字段，详见页面配置 |
| patrolSituation  | positional_management.inspection_task.patrolSituation | 模块表单/列表字段，详见页面配置 |
| issuePersonName  | positional_management.inspection_task.issuePerson     | 模块表单/列表字段，详见页面配置 |
| principalName    | positional_management.inspection_task.principal       | 模块表单/列表字段，详见页面配置 |
| patrolLeaderName | positional_management.inspection_task.patrolLeader    | 模块表单/列表字段，详见页面配置 |
| patrolReason     | positional_management.inspection_task.patrolReason    | 模块表单/列表字段，详见页面配置 |
| joinPerson       | positional_management.inspection_task.joinPerson      | 模块表单/列表字段，详见页面配置 |
| remark           | positional_management.inspection_task.remark          | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

- 新建/新增
- 编辑
- 详情回填
- 导出
- 导入
- 复制
- 启用/停用

---

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                                           | 关系说明                                         |
| -------------------------------------------------- | ------------------------------------------------ |
| 巡检点管理（inspection_point_management）          | 同级功能模块，可共同构成「阵地巡检管理」业务能力 |
| 巡检项目管理（inspection_project_management）      | 同级功能模块，可共同构成「阵地巡检管理」业务能力 |
| 巡检任务操作记录（inspection_task_operate_record） | 同级功能模块，可共同构成「阵地巡检管理」业务能力 |
| 例行巡检（routine_inspection）                     | 同级功能模块，可共同构成「阵地巡检管理」业务能力 |
| 例行巡检方案（routine_inspection_scheme）          | 同级功能模块，可共同构成「阵地巡检管理」业务能力 |

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

本模块（`routine_inspection_task`）位于 `src/pages/config_management/positional_management/inspection_management/routine_inspection_task`，归属「阵地巡检管理」。它负责「例行巡检任务」相关业务的页面交互与数据读写。维护本模块时，请同步关注接口契约、字段语义及与兄弟模块的数据一致性。

---

## 8. 接口清单

以下接口由本模块页面代码直接或通过 `@/services` Controller 调用，参数与响应 Schema 来自平台 OpenAPI（若可匹配）。

### 8.1 InspectionTaskItem

| 项       | 内容                                                |
| -------- | --------------------------------------------------- |
| 接口路径 | `未知`                                              |
| 请求方法 | `未知`                                              |
| 前端封装 | `PositionalInspectionController.InspectionTaskItem` |
| 作用说明 | 见模块业务逻辑                                      |

_未在平台 OpenAPI 中匹配到该路径；请以实际 Controller 封装与网络请求为准。_

---

### 8.2 查询巡检点位分页列表

| 项          | 内容                                                |
| ----------- | --------------------------------------------------- |
| 接口路径    | `/patrolPoint/getPatrolPointPage`                   |
| 请求方法    | `POST`                                              |
| 前端封装    | `PositionalInspectionController.getPatrolPointPage` |
| Swagger Tag | patrolPointApi                                      |
| 作用说明    | 查询巡检点位分页列表                                |

**请求参数（Body）：**

| 字段             | 类型             | 说明 |
| ---------------- | ---------------- | ---- |
| `page`           | `integer`        |      |
| `size`           | `integer`        |      |
| `search`         | `string`         |      |
| `fieldList`      | `array<string>`  |      |
| `sorter`         | `array<object>`  |      |
| `sorter[].order` | `string`         |      |
| `sorter[].field` | `string`         |      |
| `exportIds`      | `array<integer>` |      |
| `exportSize`     | `integer`        |      |
| `pointName`      | `string`         |      |
| `pointType`      | `integer`        |      |

**响应体：**

| 字段                          | 类型             | 说明                              |
| ----------------------------- | ---------------- | --------------------------------- |
| `code`                        | `integer`        |                                   |
| `message`                     | `string`         |                                   |
| `data`                        | `object`         |                                   |
| `data.records`                | `array<object>`  | 查询数据列表                      |
| `data.records[].id`           | `integer`        |                                   |
| `data.records[].pointName`    | `string`         |                                   |
| `data.records[].pointType`    | `array<integer>` |                                   |
| `data.records[].remark`       | `string`         |                                   |
| `data.records[].pointTypeStr` | `string`         |                                   |
| `data.records[].createdTime`  | `string`         |                                   |
| `data.records[].updatedTime`  | `string`         |                                   |
| `data.total`                  | `integer`        | 总数                              |
| `data.size`                   | `integer`        | 每页显示条数，默认 10             |
| `data.current`                | `integer`        | 当前页                            |
| `data.orders`                 | `array<object>`  | 排序字段信息                      |
| `data.orders[].column`        | `string`         | 需要进行排序的字段                |
| `data.orders[].asc`           | `boolean`        | 是否正序排列，默认 true           |
| `data.optimizeCountSql`       | `boolean`        | 自动优化 COUNT SQL                |
| `data.searchCount`            | `boolean`        | 是否进行 count 查询               |
| `data.optimizeJoinOfCountSql` | `boolean`        | {@link #optimizeJoinOfCountSql()} |
| `data.countId`                | `string`         | countId                           |
| `data.maxLimit`               | `integer`        | countId                           |

---

### 8.3 查询巡检/检查项目分页列表

| 项          | 内容                                                  |
| ----------- | ----------------------------------------------------- |
| 接口路径    | `/patrolProject/getPatrolProjectPage`                 |
| 请求方法    | `POST`                                                |
| 前端封装    | `PositionalInspectionController.getPatrolProjectPage` |
| Swagger Tag | patrolProjectApi                                      |
| 作用说明    | 查询巡检/检查项目分页列表                             |

**请求参数（Body）：**

| 字段             | 类型             | 说明 |
| ---------------- | ---------------- | ---- |
| `page`           | `integer`        |      |
| `size`           | `integer`        |      |
| `search`         | `string`         |      |
| `fieldList`      | `array<string>`  |      |
| `sorter`         | `array<object>`  |      |
| `sorter[].order` | `string`         |      |
| `sorter[].field` | `string`         |      |
| `exportIds`      | `array<integer>` |      |
| `exportSize`     | `integer`        |      |
| `projectName`    | `string`         |      |
| `projectType`    | `integer`        |      |

**响应体：**

| 字段                            | 类型            | 说明                              |
| ------------------------------- | --------------- | --------------------------------- |
| `code`                          | `integer`       |                                   |
| `message`                       | `string`        |                                   |
| `data`                          | `object`        |                                   |
| `data.records`                  | `array<object>` | 查询数据列表                      |
| `data.records[].id`             | `integer`       |                                   |
| `data.records[].projectName`    | `string`        |                                   |
| `data.records[].projectContent` | `string`        |                                   |
| `data.records[].projectType`    | `integer`       | 1: 巡查项目，2: 检查项目          |
| `data.records[].remark`         | `string`        |                                   |
| `data.records[].createdTime`    | `string`        |                                   |
| `data.records[].updatedTime`    | `string`        |                                   |
| `data.total`                    | `integer`       | 总数                              |
| `data.size`                     | `integer`       | 每页显示条数，默认 10             |
| `data.current`                  | `integer`       | 当前页                            |
| `data.orders`                   | `array<object>` | 排序字段信息                      |
| `data.orders[].column`          | `string`        | 需要进行排序的字段                |
| `data.orders[].asc`             | `boolean`       | 是否正序排列，默认 true           |
| `data.optimizeCountSql`         | `boolean`       | 自动优化 COUNT SQL                |
| `data.searchCount`              | `boolean`       | 是否进行 count 查询               |
| `data.optimizeJoinOfCountSql`   | `boolean`       | {@link #optimizeJoinOfCountSql()} |
| `data.countId`                  | `string`        | countId                           |
| `data.maxLimit`                 | `integer`       | countId                           |

---

### 8.4 获取巡检方案分页列表

| 项          | 内容                                                    |
| ----------- | ------------------------------------------------------- |
| 接口路径    | `/patrolPlan/getPatrolPlanPage`                         |
| 请求方法    | `POST`                                                  |
| 前端封装    | `PositionalInspectionController.getPatrolCyclePlanPage` |
| Swagger Tag | patrolPlanApi                                           |
| 作用说明    | 获取巡检方案分页列表                                    |

**请求参数（Body）：**

| 字段             | 类型             | 说明 |
| ---------------- | ---------------- | ---- |
| `page`           | `integer`        |      |
| `size`           | `integer`        |      |
| `search`         | `string`         |      |
| `fieldList`      | `array<string>`  |      |
| `sorter`         | `array<object>`  |      |
| `sorter[].order` | `string`         |      |
| `sorter[].field` | `string`         |      |
| `exportIds`      | `array<integer>` |      |
| `exportSize`     | `integer`        |      |
| `planName`       | `string`         |      |
| `planType`       | `string`         |      |

**响应体：**

| 字段                          | 类型            | 说明                                 |
| ----------------------------- | --------------- | ------------------------------------ |
| `code`                        | `integer`       |                                      |
| `message`                     | `string`        |                                      |
| `data`                        | `object`        |                                      |
| `data.records`                | `array<object>` | 查询数据列表                         |
| `data.records[].id`           | `integer`       |                                      |
| `data.records[].planName`     | `string`        | 方案名称                             |
| `data.records[].planType`     | `integer`       | 方案类型: 1-例行巡查，2-安全技术检查 |
| `data.records[].cycleDays`    | `integer`       | 巡检周期（/天）                      |
| `data.records[].details`      | `string`        | 点位项目信息                         |
| `data.records[].remark`       | `string`        |                                      |
| `data.records[].createdTime`  | `string`        |                                      |
| `data.records[].updatedTime`  | `string`        |                                      |
| `data.total`                  | `integer`       | 总数                                 |
| `data.size`                   | `integer`       | 每页显示条数，默认 10                |
| `data.current`                | `integer`       | 当前页                               |
| `data.orders`                 | `array<object>` | 排序字段信息                         |
| `data.orders[].column`        | `string`        | 需要进行排序的字段                   |
| `data.orders[].asc`           | `boolean`       | 是否正序排列，默认 true              |
| `data.optimizeCountSql`       | `boolean`       | 自动优化 COUNT SQL                   |
| `data.searchCount`            | `boolean`       | 是否进行 count 查询                  |
| `data.optimizeJoinOfCountSql` | `boolean`       | {@link #optimizeJoinOfCountSql()}    |
| `data.countId`                | `string`        | countId                              |
| `data.maxLimit`               | `integer`       | countId                              |

---

### 8.5 查询巡检任务

| 项          | 内容                                               |
| ----------- | -------------------------------------------------- |
| 接口路径    | `/patrolTask/queryPatrolTask`                      |
| 请求方法    | `POST`                                             |
| 前端封装    | `PositionalInspectionController.getInspectionTask` |
| Swagger Tag | patrolTaskApi                                      |
| 作用说明    | 查询巡检任务                                       |

**请求参数（Body）：**

| 字段              | 类型             | 说明 |
| ----------------- | ---------------- | ---- |
| `id`              | `integer`        |      |
| `taskName`        | `string`         |      |
| `taskType`        | `integer`        |      |
| `startTime`       | `string`         |      |
| `endTime`         | `string`         |      |
| `taskStatus`      | `integer`        |      |
| `issuePersonId`   | `integer`        |      |
| `patrolSituation` | `string`         |      |
| `principalId`     | `integer`        |      |
| `joinPerson`      | `string`         |      |
| `patrolReason`    | `string`         |      |
| `patrolLeaderId`  | `integer`        |      |
| `remark`          | `string`         |      |
| `patrolPlanId`    | `integer`        |      |
| `cycleDays`       | `integer`        |      |
| `details`         | `string`         |      |
| `ids`             | `array<integer>` |      |

**响应体：**

| 字段                    | 类型      | 说明 |
| ----------------------- | --------- | ---- |
| `code`                  | `integer` |      |
| `message`               | `string`  |      |
| `data`                  | `object`  |      |
| `data.id`               | `integer` |      |
| `data.taskName`         | `string`  |      |
| `data.taskType`         | `integer` |      |
| `data.startTime`        | `string`  |      |
| `data.endTime`          | `string`  |      |
| `data.taskStatus`       | `integer` |      |
| `data.taskStatusName`   | `string`  |      |
| `data.issuePersonId`    | `integer` |      |
| `data.issuePersonName`  | `string`  |      |
| `data.patrolSituation`  | `string`  |      |
| `data.principalId`      | `integer` |      |
| `data.principalName`    | `string`  |      |
| `data.joinPerson`       | `string`  |      |
| `data.patrolReason`     | `string`  |      |
| `data.patrolLeaderId`   | `integer` |      |
| `data.patrolLeaderName` | `string`  |      |
| `data.remark`           | `string`  |      |
| `data.patrolPlanId`     | `integer` |      |
| `data.patrolPlanName`   | `string`  |      |
| `data.cycleDays`        | `integer` |      |
| `data.details`          | `string`  |      |
| `data.createdTime`      | `string`  |      |
| `data.updatedTime`      | `string`  |      |

---

### 8.6 获取巡检方案

| 项          | 内容                                                |
| ----------- | --------------------------------------------------- |
| 接口路径    | `/patrolPlan/getPatrolPlan`                         |
| 请求方法    | `POST`                                              |
| 前端封装    | `PositionalInspectionController.getPatrolCyclePlan` |
| Swagger Tag | patrolPlanApi                                       |
| 作用说明    | 获取巡检方案                                        |

**请求参数（Body）：**

| 字段        | 类型             | 说明 |
| ----------- | ---------------- | ---- |
| `id`        | `integer`        |      |
| `planName`  | `string`         |      |
| `planType`  | `integer`        |      |
| `cycleDays` | `integer`        |      |
| `details`   | `string`         |      |
| `remark`    | `string`         |      |
| `ids`       | `array<integer>` |      |

**响应体：**

| 字段               | 类型      | 说明                                 |
| ------------------ | --------- | ------------------------------------ |
| `code`             | `integer` |                                      |
| `message`          | `string`  |                                      |
| `data`             | `object`  |                                      |
| `data.id`          | `integer` |                                      |
| `data.planName`    | `string`  | 方案名称                             |
| `data.planType`    | `integer` | 方案类型: 1-例行巡查，2-安全技术检查 |
| `data.cycleDays`   | `integer` | 巡检周期（/天）                      |
| `data.details`     | `string`  | 点位项目信息                         |
| `data.remark`      | `string`  |                                      |
| `data.createdTime` | `string`  |                                      |
| `data.updatedTime` | `string`  |                                      |

---

### 8.7 修改巡检任务

| 项          | 内容                                                  |
| ----------- | ----------------------------------------------------- |
| 接口路径    | `/patrolTask/updatePatrolTask`                        |
| 请求方法    | `POST`                                                |
| 前端封装    | `PositionalInspectionController.updateInspectionTask` |
| Swagger Tag | patrolTaskApi                                         |
| 作用说明    | 修改巡检任务                                          |

**请求参数（Body）：**

| 字段              | 类型             | 说明 |
| ----------------- | ---------------- | ---- |
| `id`              | `integer`        |      |
| `taskName`        | `string`         |      |
| `taskType`        | `integer`        |      |
| `startTime`       | `string`         |      |
| `endTime`         | `string`         |      |
| `taskStatus`      | `integer`        |      |
| `issuePersonId`   | `integer`        |      |
| `patrolSituation` | `string`         |      |
| `principalId`     | `integer`        |      |
| `joinPerson`      | `string`         |      |
| `patrolReason`    | `string`         |      |
| `patrolLeaderId`  | `integer`        |      |
| `remark`          | `string`         |      |
| `patrolPlanId`    | `integer`        |      |
| `cycleDays`       | `integer`        |      |
| `details`         | `string`         |      |
| `ids`             | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.8 新增巡检任务

| 项          | 内容                                               |
| ----------- | -------------------------------------------------- |
| 接口路径    | `/patrolTask/addPatrolTask`                        |
| 请求方法    | `POST`                                             |
| 前端封装    | `PositionalInspectionController.addInspectionTask` |
| Swagger Tag | patrolTaskApi                                      |
| 作用说明    | 新增巡检任务                                       |

**请求参数（Body）：**

| 字段              | 类型             | 说明 |
| ----------------- | ---------------- | ---- |
| `id`              | `integer`        |      |
| `taskName`        | `string`         |      |
| `taskType`        | `integer`        |      |
| `startTime`       | `string`         |      |
| `endTime`         | `string`         |      |
| `taskStatus`      | `integer`        |      |
| `issuePersonId`   | `integer`        |      |
| `patrolSituation` | `string`         |      |
| `principalId`     | `integer`        |      |
| `joinPerson`      | `string`         |      |
| `patrolReason`    | `string`         |      |
| `patrolLeaderId`  | `integer`        |      |
| `remark`          | `string`         |      |
| `patrolPlanId`    | `integer`        |      |
| `cycleDays`       | `integer`        |      |
| `details`         | `string`         |      |
| `ids`             | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.9 获取巡检任务分页列表

| 项          | 内容                                                   |
| ----------- | ------------------------------------------------------ |
| 接口路径    | `/patrolTask/getPatrolTaskPage`                        |
| 请求方法    | `POST`                                                 |
| 前端封装    | `PositionalInspectionController.getInspectionTaskPage` |
| Swagger Tag | patrolTaskApi                                          |
| 作用说明    | 获取巡检任务分页列表                                   |

**请求参数（Body）：**

| 字段              | 类型             | 说明 |
| ----------------- | ---------------- | ---- |
| `page`            | `integer`        |      |
| `size`            | `integer`        |      |
| `search`          | `string`         |      |
| `fieldList`       | `array<string>`  |      |
| `sorter`          | `array<object>`  |      |
| `sorter[].order`  | `string`         |      |
| `sorter[].field`  | `string`         |      |
| `exportIds`       | `array<integer>` |      |
| `exportSize`      | `integer`        |      |
| `taskName`        | `string`         |      |
| `taskType`        | `integer`        |      |
| `taskStatus`      | `integer`        |      |
| `startTime`       | `string`         |      |
| `endTime`         | `string`         |      |
| `patrolSituation` | `string`         |      |

**响应体：**

| 字段                              | 类型            | 说明                              |
| --------------------------------- | --------------- | --------------------------------- |
| `code`                            | `integer`       |                                   |
| `message`                         | `string`        |                                   |
| `data`                            | `object`        |                                   |
| `data.records`                    | `array<object>` | 查询数据列表                      |
| `data.records[].id`               | `integer`       |                                   |
| `data.records[].taskName`         | `string`        |                                   |
| `data.records[].taskType`         | `integer`       |                                   |
| `data.records[].startTime`        | `string`        |                                   |
| `data.records[].endTime`          | `string`        |                                   |
| `data.records[].taskStatus`       | `integer`       |                                   |
| `data.records[].taskStatusName`   | `string`        |                                   |
| `data.records[].issuePersonId`    | `integer`       |                                   |
| `data.records[].issuePersonName`  | `string`        |                                   |
| `data.records[].patrolSituation`  | `string`        |                                   |
| `data.records[].principalId`      | `integer`       |                                   |
| `data.records[].principalName`    | `string`        |                                   |
| `data.records[].joinPerson`       | `string`        |                                   |
| `data.records[].patrolReason`     | `string`        |                                   |
| `data.records[].patrolLeaderId`   | `integer`       |                                   |
| `data.records[].patrolLeaderName` | `string`        |                                   |
| `data.records[].remark`           | `string`        |                                   |
| `data.records[].patrolPlanId`     | `integer`       |                                   |
| `data.records[].patrolPlanName`   | `string`        |                                   |
| `data.records[].cycleDays`        | `integer`       |                                   |
| `data.records[].details`          | `string`        |                                   |
| `data.records[].createdTime`      | `string`        |                                   |
| `data.records[].updatedTime`      | `string`        |                                   |
| `data.total`                      | `integer`       | 总数                              |
| `data.size`                       | `integer`       | 每页显示条数，默认 10             |
| `data.current`                    | `integer`       | 当前页                            |
| `data.orders`                     | `array<object>` | 排序字段信息                      |
| `data.orders[].column`            | `string`        | 需要进行排序的字段                |
| `data.orders[].asc`               | `boolean`       | 是否正序排列，默认 true           |
| `data.optimizeCountSql`           | `boolean`       | 自动优化 COUNT SQL                |
| `data.searchCount`                | `boolean`       | 是否进行 count 查询               |
| `data.optimizeJoinOfCountSql`     | `boolean`       | {@link #optimizeJoinOfCountSql()} |
| `data.countId`                    | `string`        | countId                           |
| `data.maxLimit`                   | `integer`       | countId                           |

---

### 8.10 删除巡检任务

| 项          | 内容                                                  |
| ----------- | ----------------------------------------------------- |
| 接口路径    | `/patrolTask/deletePatrolTask`                        |
| 请求方法    | `POST`                                                |
| 前端封装    | `PositionalInspectionController.deleteInspectionTask` |
| Swagger Tag | patrolTaskApi                                         |
| 作用说明    | 删除巡检任务                                          |

**请求参数（Body）：**

| 字段              | 类型             | 说明 |
| ----------------- | ---------------- | ---- |
| `id`              | `integer`        |      |
| `taskName`        | `string`         |      |
| `taskType`        | `integer`        |      |
| `startTime`       | `string`         |      |
| `endTime`         | `string`         |      |
| `taskStatus`      | `integer`        |      |
| `issuePersonId`   | `integer`        |      |
| `patrolSituation` | `string`         |      |
| `principalId`     | `integer`        |      |
| `joinPerson`      | `string`         |      |
| `patrolReason`    | `string`         |      |
| `patrolLeaderId`  | `integer`        |      |
| `remark`          | `string`         |      |
| `patrolPlanId`    | `integer`        |      |
| `cycleDays`       | `integer`        |      |
| `details`         | `string`         |      |
| `ids`             | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.11 修改巡检任务状态

| 项          | 内容                                                        |
| ----------- | ----------------------------------------------------------- |
| 接口路径    | `/patrolTask/updatePatrolTaskStatus`                        |
| 请求方法    | `POST`                                                      |
| 前端封装    | `PositionalInspectionController.updateInspectionTaskStatus` |
| Swagger Tag | patrolTaskApi                                               |
| 作用说明    | 修改巡检任务状态                                            |

**请求参数（Body）：**

| 字段              | 类型             | 说明 |
| ----------------- | ---------------- | ---- |
| `id`              | `integer`        |      |
| `taskName`        | `string`         |      |
| `taskType`        | `integer`        |      |
| `startTime`       | `string`         |      |
| `endTime`         | `string`         |      |
| `taskStatus`      | `integer`        |      |
| `issuePersonId`   | `integer`        |      |
| `patrolSituation` | `string`         |      |
| `principalId`     | `integer`        |      |
| `joinPerson`      | `string`         |      |
| `patrolReason`    | `string`         |      |
| `patrolLeaderId`  | `integer`        |      |
| `remark`          | `string`         |      |
| `patrolPlanId`    | `integer`        |      |
| `cycleDays`       | `integer`        |      |
| `details`         | `string`         |      |
| `ids`             | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---
