# 组织机构（organization）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                   |
| ------------------ | ------------------------------------------------------ |
| 模块名称（中文）   | 组织机构                                               |
| 模块名称（英文）   | Organization                                           |
| 所属 Group（中文） | 用户权限                                               |
| 所属 Group（英文） | User & Auth                                            |
| Group ID           | `user`                                                 |
| 菜单位置           | 配置管理平台 → 系统管理 → 用户权限 → 组织机构          |
| 路由路径           | `/config_management/system/user/organization`          |
| 页面目录           | `src/pages/config_management/system/user/organization` |

## 1. 模块定位与项目作用

组织机构是综合信息平台中「用户权限」业务域下的功能模块，对应页面目录 `src/pages/config_management/system/user/organization`。

在项目中的主要作用：

- 作为「配置管理平台 → 系统管理 → 用户权限 → 组织机构」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
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

| 字段名                | 中文含义     | 作用说明                        |
| --------------------- | ------------ | ------------------------------- |
| weight                | 权重         | 模块表单/列表字段，详见页面配置 |
| inCode                | 部队内码     | 模块表单/列表字段，详见页面配置 |
| armyDesignation       | 部队番号     | 模块表单/列表字段，详见页面配置 |
| organizeName          | 单位简称     | 模块表单/列表字段，详见页面配置 |
| outName               | 对外名称     | 模块表单/列表字段，详见页面配置 |
| unitCode              | 单位编号     | 模块表单/列表字段，详见页面配置 |
| unitSymbol            | 单位代号     | 模块表单/列表字段，详见页面配置 |
| contactPhone          | 联系电话     | 模块表单/列表字段，详见页面配置 |
| zipCode               | 邮政编码     | 模块表单/列表字段，详见页面配置 |
| armyDivisionId        | 部队划分     | 模块表单/列表字段，详见页面配置 |
| armyCode              | 部队序号     | 模块表单/列表字段，详见页面配置 |
| authorizedCode        | 编制序号     | 模块表单/列表字段，详见页面配置 |
| authorizedDesignation | 编制番号     | 模块表单/列表字段，详见页面配置 |
| authorizedName        | 编制简称     | 模块表单/列表字段，详见页面配置 |
| armyCategoryId        | 部队类别     | 模块表单/列表字段，详见页面配置 |
| unitLevelId           | 单位级别     | 模块表单/列表字段，详见页面配置 |
| authorizedCategoryId  | 编成类别     | 模块表单/列表字段，详见页面配置 |
| longitude             | 经度         | 模块表单/列表字段，详见页面配置 |
| latitude              | 纬度         | 模块表单/列表字段，详见页面配置 |
| unitIntroduction      | 单位介绍     | 模块表单/列表字段，详见页面配置 |
| contactAddress        | 通讯地址     | 模块表单/列表字段，详见页面配置 |
| remark                | 备注         | 模块表单/列表字段，详见页面配置 |
| parentId              | 父单位       | 模块表单/列表字段，详见页面配置 |
| attach                | 图片         | 模块表单/列表字段，详见页面配置 |
| isExtend              | 是否扩展单位 | 模块表单/列表字段，详见页面配置 |
| isWar                 | 是否参战     | 模块表单/列表字段，详见页面配置 |
| authorizedSymbol      | 编制代号     | 模块表单/列表字段，详见页面配置 |
| groupTime             | 编组时间     | 模块表单/列表字段，详见页面配置 |
| armyCharZh            | 军标代字(汉) | 模块表单/列表字段，详见页面配置 |
| armyCharCn            | 军标代字     | 模块表单/列表字段，详见页面配置 |
| armySymbol            | 军标代号     | 模块表单/列表字段，详见页面配置 |
| historicalEvolution   | 历史沿革     | 模块表单/列表字段，详见页面配置 |
| undertakeTask         | 担负任务     | 模块表单/列表字段，详见页面配置 |
| organizeCategoryId    | 建制类别     | 模块表单/列表字段，详见页面配置 |
| warZone               | 战区         | 模块表单/列表字段，详见页面配置 |
| authorizedTypeId      | 编成类别细分 | 模块表单/列表字段，详见页面配置 |
| armedCategoryId       | 武装力量区分 | 模块表单/列表字段，详见页面配置 |
| armedTypeId           | 军种         | 模块表单/列表字段，详见页面配置 |
| strategyDirectionId   | 战略方向     | 模块表单/列表字段，详见页面配置 |
| supplyNatureId        | 供应性质     | 模块表单/列表字段，详见页面配置 |
| guardZoneId           | 保障区       | 模块表单/列表字段，详见页面配置 |
| soldierCategoryId     | 兵种         | 模块表单/列表字段，详见页面配置 |
| resume                | 简述         | 模块表单/列表字段，详见页面配置 |
| file                  | file         | 模块表单/列表字段，详见页面配置 |
| 图片                  | 图片         | 模块表单/列表字段，详见页面配置 |

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

| 关联模块                  | 关系说明                                     |
| ------------------------- | -------------------------------------------- |
| 文件分类（file_category） | 同级功能模块，可共同构成「用户权限」业务能力 |
| 菜单管理（menu_manage）   | 同级功能模块，可共同构成「用户权限」业务能力 |
| 模块管理（module_manage） | 同级功能模块，可共同构成「用户权限」业务能力 |
| 角色授权（role_auth）     | 同级功能模块，可共同构成「用户权限」业务能力 |
| 角色管理（role_manage）   | 同级功能模块，可共同构成「用户权限」业务能力 |
| 用户组（user_group）      | 同级功能模块，可共同构成「用户权限」业务能力 |
| 用户管理（user_manage）   | 同级功能模块，可共同构成「用户权限」业务能力 |

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

本模块（`organization`）位于 `src/pages/config_management/system/user/organization`，归属「用户权限」。它负责「组织机构」相关业务的页面交互与数据读写。维护本模块时，请同步关注接口契约、字段语义及与兄弟模块的数据一致性。

---

## 8. 接口清单

以下接口由本模块页面代码直接或通过 `@/services` Controller 调用，参数与响应 Schema 来自 `swaggerApi.json`（若可匹配）。

### 8.1 获取组织树

| 项          | 内容                               |
| ----------- | ---------------------------------- |
| 接口路径    | `/organize/getOrganizeTree`        |
| 请求方法    | `POST`                             |
| 前端封装    | `SystemController.getOrganizeTree` |
| Swagger Tag | organizationApi                    |
| 作用说明    | 获取组织树                         |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.2 获取组织列表

| 项          | 内容                               |
| ----------- | ---------------------------------- |
| 接口路径    | `/organize/getOrganizeList`        |
| 请求方法    | `POST`                             |
| 前端封装    | `SystemController.getOrganizeList` |
| Swagger Tag | organizationApi                    |
| 作用说明    | 获取组织列表                       |

**请求参数（Body）：**

| 字段           | 类型            | 说明 |
| -------------- | --------------- | ---- |
| `page`         | `integer`       |      |
| `size`         | `integer`       |      |
| `search`       | `string`        |      |
| `fieldList`    | `array<string>` |      |
| `organizeName` | `string`        |      |
| `outName`      | `string`        |      |
| `unitCode`     | `string`        |      |
| `unitSymbol`   | `string`        |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.3 导出组织列表

| 项          | 内容                                  |
| ----------- | ------------------------------------- |
| 接口路径    | `/organize/writerOrganizeList`        |
| 请求方法    | `GET`                                 |
| 前端封装    | `SystemController.writerOrganizeList` |
| Swagger Tag | organizationApi                       |
| 作用说明    | 导出组织列表                          |

**Query/Path 参数：**

| 参数名         | 位置  | 必填 | 类型     | 说明 |
| -------------- | ----- | ---- | -------- | ---- |
| `page`         | query | 是   | `string` |      |
| `size`         | query | 是   | `string` |      |
| `search`       | query | 否   | `string` |      |
| `fieldList[0]` | query | 否   | `string` |      |
| `organizeName` | query | 否   | `string` |      |
| `outName`      | query | 否   | `string` |      |
| `unitCode`     | query | 否   | `string` |      |
| `unitSymbol`   | query | 否   | `string` |      |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

---

### 8.4 添加组织

| 项          | 内容                           |
| ----------- | ------------------------------ |
| 接口路径    | `/organize/addOrganize`        |
| 请求方法    | `POST`                         |
| 前端封装    | `SystemController.addOrganize` |
| Swagger Tag | organizationApi                |
| 作用说明    | 添加组织                       |

**请求参数（Body）：**

| 字段                    | 类型             | 说明 |
| ----------------------- | ---------------- | ---- |
| `id`                    | `integer`        |      |
| `organizeName`          | `string`         |      |
| `parentId`              | `integer`        |      |
| `weight`                | `integer`        |      |
| `inCode`                | `string`         |      |
| `attach`                | `string`         |      |
| `authorizedName`        | `string`         |      |
| `armyDivisionId`        | `integer`        |      |
| `armyCode`              | `string`         |      |
| `authorizedCode`        | `string`         |      |
| `unitCode`              | `string`         |      |
| `unitSymbol`            | `string`         |      |
| `armyDesignation`       | `string`         |      |
| `authorizedDesignation` | `string`         |      |
| `outName`               | `string`         |      |
| `zipCode`               | `string`         |      |
| `contactPhone`          | `string`         |      |
| `contactAddress`        | `string`         |      |
| `authorizedCategoryId`  | `integer`        |      |
| `armyCategoryId`        | `integer`        |      |
| `unitLevelId`           | `integer`        |      |
| `longitude`             | `string`         |      |
| `latitude`              | `string`         |      |
| `isExtend`              | `integer`        |      |
| `organizeCategoryId`    | `integer`        |      |
| `soldierCategoryId`     | `integer`        |      |
| `warZone`               | `integer`        |      |
| `authorizedTypeId`      | `integer`        |      |
| `armedCategoryId`       | `integer`        |      |
| `armedTypeId`           | `integer`        |      |
| `strategyDirectionId`   | `integer`        |      |
| `supplyNatureId`        | `integer`        |      |
| `guardZoneId`           | `integer`        |      |
| `groupTime`             | `string`         |      |
| `authorizedSymbol`      | `string`         |      |
| `isWar`                 | `integer`        |      |
| `armyCharZh`            | `string`         |      |
| `armyCharCn`            | `string`         |      |
| `armySymbol`            | `string`         |      |
| `unitIntroduction`      | `string`         |      |
| `historicalEvolution`   | `string`         |      |
| `undertakeTask`         | `string`         |      |
| `resume`                | `string`         |      |
| `remark`                | `string`         |      |
| `ids`                   | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.5 获取组织信息

| 项          | 内容                               |
| ----------- | ---------------------------------- |
| 接口路径    | `/organize/getOrganizeInfo`        |
| 请求方法    | `POST`                             |
| 前端封装    | `SystemController.getOrganizeInfo` |
| Swagger Tag | organizationApi                    |
| 作用说明    | 获取组织信息                       |

**请求参数（Body）：**

| 字段                    | 类型             | 说明 |
| ----------------------- | ---------------- | ---- |
| `id`                    | `integer`        |      |
| `organizeName`          | `string`         |      |
| `parentId`              | `integer`        |      |
| `weight`                | `integer`        |      |
| `inCode`                | `string`         |      |
| `attach`                | `string`         |      |
| `authorizedName`        | `string`         |      |
| `armyDivisionId`        | `integer`        |      |
| `armyCode`              | `string`         |      |
| `authorizedCode`        | `string`         |      |
| `unitCode`              | `string`         |      |
| `unitSymbol`            | `string`         |      |
| `armyDesignation`       | `string`         |      |
| `authorizedDesignation` | `string`         |      |
| `outName`               | `string`         |      |
| `zipCode`               | `string`         |      |
| `contactPhone`          | `string`         |      |
| `contactAddress`        | `string`         |      |
| `authorizedCategoryId`  | `integer`        |      |
| `armyCategoryId`        | `integer`        |      |
| `unitLevelId`           | `integer`        |      |
| `longitude`             | `string`         |      |
| `latitude`              | `string`         |      |
| `isExtend`              | `integer`        |      |
| `organizeCategoryId`    | `integer`        |      |
| `soldierCategoryId`     | `integer`        |      |
| `warZone`               | `integer`        |      |
| `authorizedTypeId`      | `integer`        |      |
| `armedCategoryId`       | `integer`        |      |
| `armedTypeId`           | `integer`        |      |
| `strategyDirectionId`   | `integer`        |      |
| `supplyNatureId`        | `integer`        |      |
| `guardZoneId`           | `integer`        |      |
| `groupTime`             | `string`         |      |
| `authorizedSymbol`      | `string`         |      |
| `isWar`                 | `integer`        |      |
| `armyCharZh`            | `string`         |      |
| `armyCharCn`            | `string`         |      |
| `armySymbol`            | `string`         |      |
| `unitIntroduction`      | `string`         |      |
| `historicalEvolution`   | `string`         |      |
| `undertakeTask`         | `string`         |      |
| `resume`                | `string`         |      |
| `remark`                | `string`         |      |
| `ids`                   | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.6 修改组织

| 项          | 内容                            |
| ----------- | ------------------------------- |
| 接口路径    | `/organize/editOrganize`        |
| 请求方法    | `POST`                          |
| 前端封装    | `SystemController.editOrganize` |
| Swagger Tag | organizationApi                 |
| 作用说明    | 修改组织                        |

**请求参数（Body）：**

| 字段                    | 类型             | 说明 |
| ----------------------- | ---------------- | ---- |
| `id`                    | `integer`        |      |
| `organizeName`          | `string`         |      |
| `parentId`              | `integer`        |      |
| `weight`                | `integer`        |      |
| `inCode`                | `string`         |      |
| `attach`                | `string`         |      |
| `authorizedName`        | `string`         |      |
| `armyDivisionId`        | `integer`        |      |
| `armyCode`              | `string`         |      |
| `authorizedCode`        | `string`         |      |
| `unitCode`              | `string`         |      |
| `unitSymbol`            | `string`         |      |
| `armyDesignation`       | `string`         |      |
| `authorizedDesignation` | `string`         |      |
| `outName`               | `string`         |      |
| `zipCode`               | `string`         |      |
| `contactPhone`          | `string`         |      |
| `contactAddress`        | `string`         |      |
| `authorizedCategoryId`  | `integer`        |      |
| `armyCategoryId`        | `integer`        |      |
| `unitLevelId`           | `integer`        |      |
| `longitude`             | `string`         |      |
| `latitude`              | `string`         |      |
| `isExtend`              | `integer`        |      |
| `organizeCategoryId`    | `integer`        |      |
| `soldierCategoryId`     | `integer`        |      |
| `warZone`               | `integer`        |      |
| `authorizedTypeId`      | `integer`        |      |
| `armedCategoryId`       | `integer`        |      |
| `armedTypeId`           | `integer`        |      |
| `strategyDirectionId`   | `integer`        |      |
| `supplyNatureId`        | `integer`        |      |
| `guardZoneId`           | `integer`        |      |
| `groupTime`             | `string`         |      |
| `authorizedSymbol`      | `string`         |      |
| `isWar`                 | `integer`        |      |
| `armyCharZh`            | `string`         |      |
| `armyCharCn`            | `string`         |      |
| `armySymbol`            | `string`         |      |
| `unitIntroduction`      | `string`         |      |
| `historicalEvolution`   | `string`         |      |
| `undertakeTask`         | `string`         |      |
| `resume`                | `string`         |      |
| `remark`                | `string`         |      |
| `ids`                   | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.7 delOrganizes

| 项          | 内容                            |
| ----------- | ------------------------------- |
| 接口路径    | `/organize/delOrganizes`        |
| 请求方法    | `POST`                          |
| 前端封装    | `SystemController.delOrganizes` |
| Swagger Tag | organizationApi                 |
| 作用说明    | delOrganizes                    |

**请求参数（Body）：**

| 字段                    | 类型             | 说明 |
| ----------------------- | ---------------- | ---- |
| `id`                    | `integer`        |      |
| `organizeName`          | `string`         |      |
| `parentId`              | `integer`        |      |
| `weight`                | `integer`        |      |
| `inCode`                | `string`         |      |
| `attach`                | `string`         |      |
| `authorizedName`        | `string`         |      |
| `armyDivisionId`        | `integer`        |      |
| `armyCode`              | `string`         |      |
| `authorizedCode`        | `string`         |      |
| `unitCode`              | `string`         |      |
| `unitSymbol`            | `string`         |      |
| `armyDesignation`       | `string`         |      |
| `authorizedDesignation` | `string`         |      |
| `outName`               | `string`         |      |
| `zipCode`               | `string`         |      |
| `contactPhone`          | `string`         |      |
| `contactAddress`        | `string`         |      |
| `authorizedCategoryId`  | `integer`        |      |
| `armyCategoryId`        | `integer`        |      |
| `unitLevelId`           | `integer`        |      |
| `longitude`             | `string`         |      |
| `latitude`              | `string`         |      |
| `isExtend`              | `integer`        |      |
| `organizeCategoryId`    | `integer`        |      |
| `soldierCategoryId`     | `integer`        |      |
| `warZone`               | `integer`        |      |
| `authorizedTypeId`      | `integer`        |      |
| `armedCategoryId`       | `integer`        |      |
| `armedTypeId`           | `integer`        |      |
| `strategyDirectionId`   | `integer`        |      |
| `supplyNatureId`        | `integer`        |      |
| `guardZoneId`           | `integer`        |      |
| `groupTime`             | `string`         |      |
| `authorizedSymbol`      | `string`         |      |
| `isWar`                 | `integer`        |      |
| `armyCharZh`            | `string`         |      |
| `armyCharCn`            | `string`         |      |
| `armySymbol`            | `string`         |      |
| `unitIntroduction`      | `string`         |      |
| `historicalEvolution`   | `string`         |      |
| `undertakeTask`         | `string`         |      |
| `resume`                | `string`         |      |
| `remark`                | `string`         |      |
| `ids`                   | `array<integer>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.8 获取部队划分数组

| 项          | 内容                                       |
| ----------- | ------------------------------------------ |
| 接口路径    | `/project/dic/getDicArmyDivisionArray`     |
| 请求方法    | `POST`                                     |
| 前端封装    | `SystemController.getDicArmyDivisionArray` |
| Swagger Tag | projectManagementApi                       |
| 作用说明    | 获取部队划分数组                           |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.9 获取部队类别

| 项          | 内容                                  |
| ----------- | ------------------------------------- |
| 接口路径    | `/organize/getDicArmyCategory`        |
| 请求方法    | `POST`                                |
| 前端封装    | `SystemController.getDicArmyCategory` |
| Swagger Tag | organizationApi                       |
| 作用说明    | 获取部队类别                          |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.10 获取单位级别数组

| 项          | 内容                                    |
| ----------- | --------------------------------------- |
| 接口路径    | `/project/dic/getDicUnitLevelArray`     |
| 请求方法    | `POST`                                  |
| 前端封装    | `SystemController.getDicUnitLevelArray` |
| Swagger Tag | projectManagementApi                    |
| 作用说明    | 获取单位级别数组                        |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.11 获取编成类别数组

| 项          | 内容                                             |
| ----------- | ------------------------------------------------ |
| 接口路径    | `/project/dic/getDicAuthorizedCategoryArray`     |
| 请求方法    | `POST`                                           |
| 前端封装    | `SystemController.getDicAuthorizedCategoryArray` |
| Swagger Tag | projectManagementApi                             |
| 作用说明    | 获取编成类别数组                                 |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.12 获取建制类别分页

| 项          | 内容                                      |
| ----------- | ----------------------------------------- |
| 接口路径    | `/organize/getDicOrganizeCategory`        |
| 请求方法    | `POST`                                    |
| 前端封装    | `SystemController.getDicOrganizeCategory` |
| Swagger Tag | organizationApi                           |
| 作用说明    | 获取建制类别分页                          |

**请求参数（Body）：**

| 字段        | 类型            | 说明 |
| ----------- | --------------- | ---- |
| `page`      | `integer`       |      |
| `size`      | `integer`       |      |
| `search`    | `string`        |      |
| `fieldList` | `array<string>` |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.13 获取战区

| 项          | 内容                             |
| ----------- | -------------------------------- |
| 接口路径    | `/organize/getDicWarZone`        |
| 请求方法    | `POST`                           |
| 前端封装    | `SystemController.getDicWarZone` |
| Swagger Tag | organizationApi                  |
| 作用说明    | 获取战区                         |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.14 获取编成类别细分

| 项          | 内容                                    |
| ----------- | --------------------------------------- |
| 接口路径    | `/organize/getDicAuthorizedType`        |
| 请求方法    | `POST`                                  |
| 前端封装    | `SystemController.getDicAuthorizedType` |
| Swagger Tag | organizationApi                         |
| 作用说明    | 获取编成类别细分                        |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.15 获取武装力量区分

| 项          | 内容                                   |
| ----------- | -------------------------------------- |
| 接口路径    | `/organize/getDicArmedCategory`        |
| 请求方法    | `POST`                                 |
| 前端封装    | `SystemController.getDicArmedCategory` |
| Swagger Tag | organizationApi                        |
| 作用说明    | 获取武装力量区分                       |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.16 获取军种

| 项          | 内容                               |
| ----------- | ---------------------------------- |
| 接口路径    | `/organize/getDicArmedType`        |
| 请求方法    | `POST`                             |
| 前端封装    | `SystemController.getDicArmedType` |
| Swagger Tag | organizationApi                    |
| 作用说明    | 获取军种                           |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.17 获取战略方向

| 项          | 内容                                       |
| ----------- | ------------------------------------------ |
| 接口路径    | `/organize/getDicStrategyDirection`        |
| 请求方法    | `POST`                                     |
| 前端封装    | `SystemController.getDicStrategyDirection` |
| Swagger Tag | organizationApi                            |
| 作用说明    | 获取战略方向                               |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.18 获取供应性质

| 项          | 内容                                  |
| ----------- | ------------------------------------- |
| 接口路径    | `/organize/getDicSupplyNature`        |
| 请求方法    | `POST`                                |
| 前端封装    | `SystemController.getDicSupplyNature` |
| Swagger Tag | organizationApi                       |
| 作用说明    | 获取供应性质                          |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.19 获取保障区

| 项          | 内容                               |
| ----------- | ---------------------------------- |
| 接口路径    | `/organize/getDicGuardZone`        |
| 请求方法    | `POST`                             |
| 前端封装    | `SystemController.getDicGuardZone` |
| Swagger Tag | organizationApi                    |
| 作用说明    | 获取保障区                         |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.20 获取兵种

| 项          | 内容                                     |
| ----------- | ---------------------------------------- |
| 接口路径    | `/organize/getDicSoldierCategory`        |
| 请求方法    | `POST`                                   |
| 前端封装    | `SystemController.getDicSoldierCategory` |
| Swagger Tag | organizationApi                          |
| 作用说明    | 获取兵种                                 |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---
