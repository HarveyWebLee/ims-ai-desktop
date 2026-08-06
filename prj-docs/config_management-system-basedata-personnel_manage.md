# 人员管理（personnel_manage）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                           |
| ------------------ | -------------------------------------------------------------- |
| 模块名称（中文）   | 人员管理                                                       |
| 模块名称（英文）   | Personnel Manage                                               |
| 所属 Group（中文） | 基础数据                                                       |
| 所属 Group（英文） | Base Data                                                      |
| Group ID           | `basedata`                                                     |
| 菜单位置           | 配置管理平台 → 系统管理 → 基础数据 → 人员管理                  |
| 路由路径           | `/config_management/system/basedata/personnel_manage`          |
| 页面目录           | `src/pages/config_management/system/basedata/personnel_manage` |

## 1. 模块定位与项目作用

人员管理是综合信息平台中「基础数据」业务域下的功能模块，对应页面目录 `src/pages/config_management/system/basedata/personnel_manage`。

在项目中的主要作用：

- 作为「配置管理平台 → 系统管理 → 基础数据 → 人员管理」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
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

| 字段名                        | 中文含义         | 作用说明                        |
| ----------------------------- | ---------------- | ------------------------------- |
| id                            | 姓名             | 模块表单/列表字段，详见页面配置 |
| personClassificationId        | 人员分类         | 模块表单/列表字段，详见页面配置 |
| personPositionId              | 人员定岗         | 模块表单/列表字段，详见页面配置 |
| operationBackboneId           | 操作骨干类别     | 模块表单/列表字段，详见页面配置 |
| militaryPositionLevelTime     | 单位地址         | 模块表单/列表字段，详见页面配置 |
| unitAddress                   | 家庭地址         | 模块表单/列表字段，详见页面配置 |
| homeAddress                   | 联系电话         | 模块表单/列表字段，详见页面配置 |
| graduationTime                | 毕业院校         | 模块表单/列表字段，详见页面配置 |
| majorName                     | 考评成绩         | 模块表单/列表字段，详见页面配置 |
| score                         | 实弹发射(枚数)   | 模块表单/列表字段，详见页面配置 |
| ammunitionCount               | 军人证号         | 模块表单/列表字段，详见页面配置 |
| militaryNo                    | 身份证号         | 模块表单/列表字段，详见页面配置 |
| idCardNo                      | 能力评定         | 模块表单/列表字段，详见页面配置 |
| isAction                      | 首长代号         | 模块表单/列表字段，详见页面配置 |
| keyPositionPersonCategoryId   | 关键岗位人员类别 | 模块表单/列表字段，详见页面配置 |
| majorPositionId               | 专业岗位         | 模块表单/列表字段，详见页面配置 |
| isReign                       | 顺序号           | 模块表单/列表字段，详见页面配置 |
| certificateTypeId             | 证件类型         | 模块表单/列表字段，详见页面配置 |
| technicalLevelName            | 备注             | 模块表单/列表字段，详见页面配置 |
| name                          | 姓名             | 模块表单/列表字段，详见页面配置 |
| sex                           | 性别             | 模块表单/列表字段，详见页面配置 |
| unitId                        | 单位             | 模块表单/列表字段，详见页面配置 |
| unitName                      | 单位             | 模块表单/列表字段，详见页面配置 |
| militaryRankId                | 军衔             | 模块表单/列表字段，详见页面配置 |
| militaryRankName              | 军衔             | 模块表单/列表字段，详见页面配置 |
| politicId                     | 政治面貌         | 模块表单/列表字段，详见页面配置 |
| politicName                   | 政治面貌         | 模块表单/列表字段，详见页面配置 |
| technicalPositionId           | 技术职务         | 模块表单/列表字段，详见页面配置 |
| technicalPositionName         | 技术职务         | 模块表单/列表字段，详见页面配置 |
| technicalPositionDate         | 技职时间         | 模块表单/列表字段，详见页面配置 |
| militaryRankDate              | 军衔时间         | 模块表单/列表字段，详见页面配置 |
| nationId                      | 民族             | 模块表单/列表字段，详见页面配置 |
| nationName                    | 民族             | 模块表单/列表字段，详见页面配置 |
| birth                         | 出生时间         | 模块表单/列表字段，详见页面配置 |
| birthTime                     | 出生时间         | 模块表单/列表字段，详见页面配置 |
| enlistDate                    | 入伍时间         | 模块表单/列表字段，详见页面配置 |
| enlistTime                    | 入伍时间         | 模块表单/列表字段，详见页面配置 |
| pic                           | 图片             | 模块表单/列表字段，详见页面配置 |
| provinceName                  | 籍贯             | 模块表单/列表字段，详见页面配置 |
| partyDate                     | 党团时间         | 模块表单/列表字段，详见页面配置 |
| personCategoryId              | 人员类别         | 模块表单/列表字段，详见页面配置 |
| personCategoryName            | 人员类别         | 模块表单/列表字段，详见页面配置 |
| personClassificationName      | 人员分类         | 模块表单/列表字段，详见页面配置 |
| personPositionName            | 人员定岗         | 模块表单/列表字段，详见页面配置 |
| operationBackboneName         | 操作骨干类别     | 模块表单/列表字段，详见页面配置 |
| militaryPositionId            | 职务             | 模块表单/列表字段，详见页面配置 |
| militaryPositionName          | 职务             | 模块表单/列表字段，详见页面配置 |
| militaryPositionDate          | 任现职时间       | 模块表单/列表字段，详见页面配置 |
| militaryPositionLevelId       | 职级             | 模块表单/列表字段，详见页面配置 |
| militaryPositionLevelName     | 职级             | 模块表单/列表字段，详见页面配置 |
| militaryPositionLevelDate     | 职级时间         | 模块表单/列表字段，详见页面配置 |
| mobile                        | 联系电话         | 模块表单/列表字段，详见页面配置 |
| workMajorId                   | 从事专业         | 模块表单/列表字段，详见页面配置 |
| workMajorName                 | 从事专业         | 模块表单/列表字段，详见页面配置 |
| graduationDate                | 毕业时间         | 模块表单/列表字段，详见页面配置 |
| university                    | 毕业院校         | 模块表单/列表字段，详见页面配置 |
| firstEducationId              | 第一学历         | 模块表单/列表字段，详见页面配置 |
| firstEducationName            | 第一学历         | 模块表单/列表字段，详见页面配置 |
| currentEducationId            | 现学历           | 模块表单/列表字段，详见页面配置 |
| currentEducationName          | 现学历           | 模块表单/列表字段，详见页面配置 |
| talentCategoryId              | 人才类别         | 模块表单/列表字段，详见页面配置 |
| talentCategoryName            | 人才类别         | 模块表单/列表字段，详见页面配置 |
| talentCategoryDate            | 人才评定时间     | 模块表单/列表字段，详见页面配置 |
| majorId                       | 所学专业         | 模块表单/列表字段，详见页面配置 |
| capabilityAssessment          | 能力评定         | 模块表单/列表字段，详见页面配置 |
| chiefNo                       | 首长代号         | 模块表单/列表字段，详见页面配置 |
| keyPositionPersonCategoryName | 关键岗位人员类别 | 模块表单/列表字段，详见页面配置 |
| isKeyPositionPerson           | 是否关键岗位人员 | 模块表单/列表字段，详见页面配置 |
| majorPositionName             | 专业岗位         | 模块表单/列表字段，详见页面配置 |
| majorPositionDate             | 现岗时间         | 模块表单/列表字段，详见页面配置 |
| sort                          | 顺序号           | 模块表单/列表字段，详见页面配置 |
| certificateTypeName           | 证件类型         | 模块表单/列表字段，详见页面配置 |
| technicalLevelId              | 技术等级         | 模块表单/列表字段，详见页面配置 |
| remark                        | 备注             | 模块表单/列表字段，详见页面配置 |
| file                          | file             | 模块表单/列表字段，详见页面配置 |
| 图片                          | 图片             | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

- 新建/新增
- 编辑
- 删除
- 导出
- 导入
- 左侧树筛选

---

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                         | 关系说明                                     |
| -------------------------------- | -------------------------------------------- |
| 门禁组（access_group）           | 同级功能模块，可共同构成「基础数据」业务能力 |
| 卡管理（card_manage）            | 同级功能模块，可共同构成「基础数据」业务能力 |
| 设备分组（device_group）         | 同级功能模块，可共同构成「基础数据」业务能力 |
| 设备类型（device_type）          | 同级功能模块，可共同构成「基础数据」业务能力 |
| 故障库（fault_library）          | 同级功能模块，可共同构成「基础数据」业务能力 |
| 哨位信息（guard_post_info）      | 同级功能模块，可共同构成「基础数据」业务能力 |
| 区间设置（interval_setting）     | 同级功能模块，可共同构成「基础数据」业务能力 |
| 监控任务（monitoring_task）      | 同级功能模块，可共同构成「基础数据」业务能力 |
| 人员统计（personnel_statistics） | 同级功能模块，可共同构成「基础数据」业务能力 |
| 区域树（region_tree）            | 同级功能模块，可共同构成「基础数据」业务能力 |

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

本模块（`personnel_manage`）位于 `src/pages/config_management/system/basedata/personnel_manage`，归属「基础数据」。它负责「人员管理」相关业务的页面交互与数据读写。维护本模块时，请同步关注接口契约、字段语义及与兄弟模块的数据一致性。

---

## 8. 接口清单

以下接口由本模块页面代码直接或通过 `@/services` Controller 调用，参数与响应 Schema 来自 `swaggerApi.json`（若可匹配）。

### 8.1 获取人员列表

| 项          | 内容                             |
| ----------- | -------------------------------- |
| 接口路径    | `/person/getPersonList`          |
| 请求方法    | `POST`                           |
| 前端封装    | `SystemController.getPersonList` |
| Swagger Tag | personnelApi                     |
| 作用说明    | 获取人员列表                     |

**请求参数（Body）：**

| 字段                        | 类型            | 说明 |
| --------------------------- | --------------- | ---- |
| `page`                      | `integer`       |      |
| `size`                      | `integer`       |      |
| `search`                    | `string`        |      |
| `fieldList`                 | `array<string>` |      |
| `militaryNo`                | `string`        |      |
| `name`                      | `string`        |      |
| `sex`                       | `integer`       |      |
| `firstEducationId`          | `integer`       |      |
| `unitId`                    | `integer`       |      |
| `militaryPositionId`        | `integer`       |      |
| `militaryRankId`            | `integer`       |      |
| `enlistDate`                | `string`        |      |
| `nationId`                  | `integer`       |      |
| `politicId`                 | `integer`       |      |
| `birth`                     | `string`        |      |
| `personCategoryId`          | `integer`       |      |
| `workMajorId`               | `integer`       |      |
| `graduationDate`            | `string`        |      |
| `majorId`                   | `integer`       |      |
| `currentEducationId`        | `integer`       |      |
| `technicalPositionId`       | `integer`       |      |
| `talentCategoryId`          | `integer`       |      |
| `militaryPositionLevelId`   | `integer`       |      |
| `militaryPositionLevelDate` | `string`        |      |
| `technicalLevelId`          | `integer`       |      |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `object`  |      |

---

### 8.2 导出人员

| 项          | 内容                            |
| ----------- | ------------------------------- |
| 接口路径    | `/person/exportPerson`          |
| 请求方法    | `GET`                           |
| 前端封装    | `SystemController.exportPerson` |
| Swagger Tag | personnelApi                    |
| 作用说明    | 导出人员                        |

**Query/Path 参数：**

| 参数名                      | 位置  | 必填 | 类型     | 说明 |
| --------------------------- | ----- | ---- | -------- | ---- |
| `page`                      | query | 是   | `string` |      |
| `size`                      | query | 是   | `string` |      |
| `search`                    | query | 否   | `string` |      |
| `fieldList[0]`              | query | 否   | `string` |      |
| `militaryNo`                | query | 否   | `string` |      |
| `name`                      | query | 否   | `string` |      |
| `sex`                       | query | 否   | `string` |      |
| `firstEducationId`          | query | 否   | `string` |      |
| `unitId`                    | query | 否   | `string` |      |
| `militaryPositionId`        | query | 否   | `string` |      |
| `militaryRankId`            | query | 否   | `string` |      |
| `enlistDate`                | query | 否   | `string` |      |
| `nationId`                  | query | 否   | `string` |      |
| `politicId`                 | query | 否   | `string` |      |
| `birth`                     | query | 否   | `string` |      |
| `personCategoryId`          | query | 否   | `string` |      |
| `workMajorId`               | query | 否   | `string` |      |
| `graduationDate`            | query | 否   | `string` |      |
| `majorId`                   | query | 否   | `string` |      |
| `currentEducationId`        | query | 否   | `string` |      |
| `technicalPositionId`       | query | 否   | `string` |      |
| `talentCategoryId`          | query | 否   | `string` |      |
| `militaryPositionLevelId`   | query | 否   | `string` |      |
| `militaryPositionLevelDate` | query | 否   | `string` |      |
| `technicalLevelId`          | query | 否   | `string` |      |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

---

### 8.3 添加人员

| 项          | 内容                         |
| ----------- | ---------------------------- |
| 接口路径    | `/person/addPerson`          |
| 请求方法    | `POST`                       |
| 前端封装    | `SystemController.addPerson` |
| Swagger Tag | personnelApi                 |
| 作用说明    | 添加人员                     |

**请求参数（Body）：**

| 字段                          | 类型             | 说明                        |
| ----------------------------- | ---------------- | --------------------------- |
| `id`                          | `integer`        |                             |
| `name`                        | `string`         |                             |
| `sex`                         | `integer`        |                             |
| `unitId`                      | `integer`        |                             |
| `nationId`                    | `integer`        |                             |
| `birth`                       | `string`         |                             |
| `enlistDate`                  | `string`         |                             |
| `pic`                         | `string`         |                             |
| `provinceName`                | `string`         | private Integer provinceId; |
| `politicId`                   | `integer`        |                             |
| `partyDate`                   | `string`         |                             |
| `personCategoryId`            | `integer`        |                             |
| `personClassificationId`      | `integer`        |                             |
| `personPositionId`            | `integer`        |                             |
| `militaryRankId`              | `integer`        |                             |
| `militaryRankDate`            | `string`         |                             |
| `operationBackboneId`         | `integer`        |                             |
| `militaryPositionId`          | `integer`        |                             |
| `militaryPositionDate`        | `string`         |                             |
| `militaryPositionLevelId`     | `integer`        |                             |
| `militaryPositionLevelDate`   | `string`         |                             |
| `unitAddress`                 | `string`         |                             |
| `homeAddress`                 | `string`         |                             |
| `mobile`                      | `string`         |                             |
| `technicalPositionId`         | `integer`        |                             |
| `technicalPositionDate`       | `string`         |                             |
| `workMajorId`                 | `integer`        |                             |
| `graduationDate`              | `string`         |                             |
| `university`                  | `string`         |                             |
| `firstEducationId`            | `integer`        |                             |
| `currentEducationId`          | `integer`        |                             |
| `talentCategoryId`            | `integer`        |                             |
| `talentCategoryDate`          | `string`         |                             |
| `majorId`                     | `integer`        |                             |
| `score`                       | `string`         |                             |
| `ammunitionCount`             | `integer`        |                             |
| `militaryNo`                  | `string`         |                             |
| `idCardNo`                    | `string`         |                             |
| `capabilityAssessment`        | `string`         |                             |
| `isAction`                    | `integer`        |                             |
| `chiefNo`                     | `string`         |                             |
| `keyPositionPersonCategoryId` | `integer`        |                             |
| `isKeyPositionPerson`         | `integer`        |                             |
| `majorPositionId`             | `integer`        |                             |
| `majorPositionDate`           | `string`         |                             |
| `isReign`                     | `integer`        |                             |
| `certificateTypeId`           | `integer`        |                             |
| `remark`                      | `string`         |                             |
| `technicalLevelId`            | `integer`        |                             |
| `sort`                        | `integer`        |                             |
| `ids`                         | `array<integer>` |                             |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.4 更新人员

| 项          | 内容                            |
| ----------- | ------------------------------- |
| 接口路径    | `/person/updatePerson`          |
| 请求方法    | `POST`                          |
| 前端封装    | `SystemController.updatePerson` |
| Swagger Tag | personnelApi                    |
| 作用说明    | 更新人员                        |

**请求参数（Body）：**

| 字段                          | 类型             | 说明                        |
| ----------------------------- | ---------------- | --------------------------- |
| `id`                          | `integer`        |                             |
| `name`                        | `string`         |                             |
| `sex`                         | `integer`        |                             |
| `unitId`                      | `integer`        |                             |
| `nationId`                    | `integer`        |                             |
| `birth`                       | `string`         |                             |
| `enlistDate`                  | `string`         |                             |
| `pic`                         | `string`         |                             |
| `provinceName`                | `string`         | private Integer provinceId; |
| `politicId`                   | `integer`        |                             |
| `partyDate`                   | `string`         |                             |
| `personCategoryId`            | `integer`        |                             |
| `personClassificationId`      | `integer`        |                             |
| `personPositionId`            | `integer`        |                             |
| `militaryRankId`              | `integer`        |                             |
| `militaryRankDate`            | `string`         |                             |
| `operationBackboneId`         | `integer`        |                             |
| `militaryPositionId`          | `integer`        |                             |
| `militaryPositionDate`        | `string`         |                             |
| `militaryPositionLevelId`     | `integer`        |                             |
| `militaryPositionLevelDate`   | `string`         |                             |
| `unitAddress`                 | `string`         |                             |
| `homeAddress`                 | `string`         |                             |
| `mobile`                      | `string`         |                             |
| `technicalPositionId`         | `integer`        |                             |
| `technicalPositionDate`       | `string`         |                             |
| `workMajorId`                 | `integer`        |                             |
| `graduationDate`              | `string`         |                             |
| `university`                  | `string`         |                             |
| `firstEducationId`            | `integer`        |                             |
| `currentEducationId`          | `integer`        |                             |
| `talentCategoryId`            | `integer`        |                             |
| `talentCategoryDate`          | `string`         |                             |
| `majorId`                     | `integer`        |                             |
| `score`                       | `string`         |                             |
| `ammunitionCount`             | `integer`        |                             |
| `militaryNo`                  | `string`         |                             |
| `idCardNo`                    | `string`         |                             |
| `capabilityAssessment`        | `string`         |                             |
| `isAction`                    | `integer`        |                             |
| `chiefNo`                     | `string`         |                             |
| `keyPositionPersonCategoryId` | `integer`        |                             |
| `isKeyPositionPerson`         | `integer`        |                             |
| `majorPositionId`             | `integer`        |                             |
| `majorPositionDate`           | `string`         |                             |
| `isReign`                     | `integer`        |                             |
| `certificateTypeId`           | `integer`        |                             |
| `remark`                      | `string`         |                             |
| `technicalLevelId`            | `integer`        |                             |
| `sort`                        | `integer`        |                             |
| `ids`                         | `array<integer>` |                             |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.5 删除人员

| 项          | 内容                            |
| ----------- | ------------------------------- |
| 接口路径    | `/person/deletePerson`          |
| 请求方法    | `POST`                          |
| 前端封装    | `SystemController.deletePerson` |
| Swagger Tag | personnelApi                    |
| 作用说明    | 删除人员                        |

**请求参数（Body）：**

| 字段                          | 类型             | 说明                        |
| ----------------------------- | ---------------- | --------------------------- |
| `id`                          | `integer`        |                             |
| `name`                        | `string`         |                             |
| `sex`                         | `integer`        |                             |
| `unitId`                      | `integer`        |                             |
| `nationId`                    | `integer`        |                             |
| `birth`                       | `string`         |                             |
| `enlistDate`                  | `string`         |                             |
| `pic`                         | `string`         |                             |
| `provinceName`                | `string`         | private Integer provinceId; |
| `politicId`                   | `integer`        |                             |
| `partyDate`                   | `string`         |                             |
| `personCategoryId`            | `integer`        |                             |
| `personClassificationId`      | `integer`        |                             |
| `personPositionId`            | `integer`        |                             |
| `militaryRankId`              | `integer`        |                             |
| `militaryRankDate`            | `string`         |                             |
| `operationBackboneId`         | `integer`        |                             |
| `militaryPositionId`          | `integer`        |                             |
| `militaryPositionDate`        | `string`         |                             |
| `militaryPositionLevelId`     | `integer`        |                             |
| `militaryPositionLevelDate`   | `string`         |                             |
| `unitAddress`                 | `string`         |                             |
| `homeAddress`                 | `string`         |                             |
| `mobile`                      | `string`         |                             |
| `technicalPositionId`         | `integer`        |                             |
| `technicalPositionDate`       | `string`         |                             |
| `workMajorId`                 | `integer`        |                             |
| `graduationDate`              | `string`         |                             |
| `university`                  | `string`         |                             |
| `firstEducationId`            | `integer`        |                             |
| `currentEducationId`          | `integer`        |                             |
| `talentCategoryId`            | `integer`        |                             |
| `talentCategoryDate`          | `string`         |                             |
| `majorId`                     | `integer`        |                             |
| `score`                       | `string`         |                             |
| `ammunitionCount`             | `integer`        |                             |
| `militaryNo`                  | `string`         |                             |
| `idCardNo`                    | `string`         |                             |
| `capabilityAssessment`        | `string`         |                             |
| `isAction`                    | `integer`        |                             |
| `chiefNo`                     | `string`         |                             |
| `keyPositionPersonCategoryId` | `integer`        |                             |
| `isKeyPositionPerson`         | `integer`        |                             |
| `majorPositionId`             | `integer`        |                             |
| `majorPositionDate`           | `string`         |                             |
| `isReign`                     | `integer`        |                             |
| `certificateTypeId`           | `integer`        |                             |
| `remark`                      | `string`         |                             |
| `technicalLevelId`            | `integer`        |                             |
| `sort`                        | `integer`        |                             |
| `ids`                         | `array<integer>` |                             |

**响应体：**

| 字段      | 类型      | 说明 |
| --------- | --------- | ---- |
| `code`    | `integer` |      |
| `message` | `string`  |      |
| `data`    | `boolean` |      |

---

### 8.6 获取组织树

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

### 8.7 获取军衔字典

| 项          | 内容                                   |
| ----------- | -------------------------------------- |
| 接口路径    | `/person/getMilitaryRankList`          |
| 请求方法    | `GET`                                  |
| 前端封装    | `SystemController.getMilitaryRankList` |
| Swagger Tag | personnelApi                           |
| 作用说明    | 获取军衔字典                           |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段          | 类型            | 说明 |
| ------------- | --------------- | ---- |
| `code`        | `integer`       |      |
| `message`     | `string`        |      |
| `data`        | `array<object>` |      |
| `data[].id`   | `integer`       |      |
| `data[].name` | `string`        |      |

---

### 8.8 获取民族字典

| 项          | 内容                             |
| ----------- | -------------------------------- |
| 接口路径    | `/person/getNationList`          |
| 请求方法    | `GET`                            |
| 前端封装    | `SystemController.getNationList` |
| Swagger Tag | personnelApi                     |
| 作用说明    | 获取民族字典                     |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段          | 类型            | 说明 |
| ------------- | --------------- | ---- |
| `code`        | `integer`       |      |
| `message`     | `string`        |      |
| `data`        | `array<object>` |      |
| `data[].id`   | `integer`       |      |
| `data[].name` | `string`        |      |

---

### 8.9 获取技术职务字典

| 项          | 内容                                        |
| ----------- | ------------------------------------------- |
| 接口路径    | `/person/getTechnicalPositionList`          |
| 请求方法    | `GET`                                       |
| 前端封装    | `SystemController.getTechnicalPositionList` |
| Swagger Tag | personnelApi                                |
| 作用说明    | 获取技术职务字典                            |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段          | 类型            | 说明 |
| ------------- | --------------- | ---- |
| `code`        | `integer`       |      |
| `message`     | `string`        |      |
| `data`        | `array<object>` |      |
| `data[].id`   | `integer`       |      |
| `data[].name` | `string`        |      |

---

### 8.10 获取人员类别字典

| 项          | 内容                                     |
| ----------- | ---------------------------------------- |
| 接口路径    | `/person/getPersonCategoryList`          |
| 请求方法    | `GET`                                    |
| 前端封装    | `SystemController.getPersonCategoryList` |
| Swagger Tag | personnelApi                             |
| 作用说明    | 获取人员类别字典                         |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段          | 类型            | 说明 |
| ------------- | --------------- | ---- |
| `code`        | `integer`       |      |
| `message`     | `string`        |      |
| `data`        | `array<object>` |      |
| `data[].id`   | `integer`       |      |
| `data[].name` | `string`        |      |

---

### 8.11 获取人员分类字典

| 项          | 内容                                           |
| ----------- | ---------------------------------------------- |
| 接口路径    | `/person/getPersonClassificationList`          |
| 请求方法    | `GET`                                          |
| 前端封装    | `SystemController.getPersonClassificationList` |
| Swagger Tag | personnelApi                                   |
| 作用说明    | 获取人员分类字典                               |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段          | 类型            | 说明 |
| ------------- | --------------- | ---- |
| `code`        | `integer`       |      |
| `message`     | `string`        |      |
| `data`        | `array<object>` |      |
| `data[].id`   | `integer`       |      |
| `data[].name` | `string`        |      |

---

### 8.12 获取人员定岗字典

| 项          | 内容                                     |
| ----------- | ---------------------------------------- |
| 接口路径    | `/person/getPersonPositionList`          |
| 请求方法    | `GET`                                    |
| 前端封装    | `SystemController.getPersonPositionList` |
| Swagger Tag | personnelApi                             |
| 作用说明    | 获取人员定岗字典                         |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段          | 类型            | 说明 |
| ------------- | --------------- | ---- |
| `code`        | `integer`       |      |
| `message`     | `string`        |      |
| `data`        | `array<object>` |      |
| `data[].id`   | `integer`       |      |
| `data[].name` | `string`        |      |

---

### 8.13 获取操作骨干类别字典

| 项          | 内容                                            |
| ----------- | ----------------------------------------------- |
| 接口路径    | `/person/getOperationBackboneTypeList`          |
| 请求方法    | `GET`                                           |
| 前端封装    | `SystemController.getOperationBackboneTypeList` |
| Swagger Tag | personnelApi                                    |
| 作用说明    | 获取操作骨干类别字典                            |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段          | 类型            | 说明 |
| ------------- | --------------- | ---- |
| `code`        | `integer`       |      |
| `message`     | `string`        |      |
| `data`        | `array<object>` |      |
| `data[].id`   | `integer`       |      |
| `data[].name` | `string`        |      |

---

### 8.14 获取职务字典树

| 项          | 内容                                       |
| ----------- | ------------------------------------------ |
| 接口路径    | `/dic/getMilitaryPositionTree`             |
| 请求方法    | `GET`                                      |
| 前端封装    | `SystemController.getMilitaryPositionTree` |
| Swagger Tag | dictionaryApi                              |
| 作用说明    | 获取职务字典树                             |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段         | 类型            | 说明 |
| ------------ | --------------- | ---- |
| `code`       | `integer`       |      |
| `message`    | `string`        |      |
| `data`       | `array<object>` |      |
| `data[].key` | `object`        |      |

---

### 8.15 获取职级字典

| 项          | 内容                                            |
| ----------- | ----------------------------------------------- |
| 接口路径    | `/person/getMilitaryPositionLevelList`          |
| 请求方法    | `GET`                                           |
| 前端封装    | `SystemController.getMilitaryPositionLevelList` |
| Swagger Tag | personnelApi                                    |
| 作用说明    | 获取职级字典                                    |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段          | 类型            | 说明 |
| ------------- | --------------- | ---- |
| `code`        | `integer`       |      |
| `message`     | `string`        |      |
| `data`        | `array<object>` |      |
| `data[].id`   | `integer`       |      |
| `data[].name` | `string`        |      |

---

### 8.16 获取从事专业字典

| 项          | 内容                                |
| ----------- | ----------------------------------- |
| 接口路径    | `/person/getWorkMajorList`          |
| 请求方法    | `GET`                               |
| 前端封装    | `SystemController.getWorkMajorList` |
| Swagger Tag | personnelApi                        |
| 作用说明    | 获取从事专业字典                    |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段          | 类型            | 说明 |
| ------------- | --------------- | ---- |
| `code`        | `integer`       |      |
| `message`     | `string`        |      |
| `data`        | `array<object>` |      |
| `data[].id`   | `integer`       |      |
| `data[].name` | `string`        |      |

---

### 8.17 获取学历字典

| 项          | 内容                                |
| ----------- | ----------------------------------- |
| 接口路径    | `/person/getEducationList`          |
| 请求方法    | `GET`                               |
| 前端封装    | `SystemController.getEducationList` |
| Swagger Tag | personnelApi                        |
| 作用说明    | 获取学历字典                        |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段          | 类型            | 说明 |
| ------------- | --------------- | ---- |
| `code`        | `integer`       |      |
| `message`     | `string`        |      |
| `data`        | `array<object>` |      |
| `data[].id`   | `integer`       |      |
| `data[].name` | `string`        |      |

---

### 8.18 获取人才类别字典

| 项          | 内容                                     |
| ----------- | ---------------------------------------- |
| 接口路径    | `/person/getTalentCategoryList`          |
| 请求方法    | `GET`                                    |
| 前端封装    | `SystemController.getTalentCategoryList` |
| Swagger Tag | personnelApi                             |
| 作用说明    | 获取人才类别字典                         |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段          | 类型            | 说明 |
| ------------- | --------------- | ---- |
| `code`        | `integer`       |      |
| `message`     | `string`        |      |
| `data`        | `array<object>` |      |
| `data[].id`   | `integer`       |      |
| `data[].name` | `string`        |      |

---

### 8.19 获取所学专业字典

| 项          | 内容                            |
| ----------- | ------------------------------- |
| 接口路径    | `/person/getMajorList`          |
| 请求方法    | `GET`                           |
| 前端封装    | `SystemController.getMajorList` |
| Swagger Tag | personnelApi                    |
| 作用说明    | 获取所学专业字典                |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段          | 类型            | 说明 |
| ------------- | --------------- | ---- |
| `code`        | `integer`       |      |
| `message`     | `string`        |      |
| `data`        | `array<object>` |      |
| `data[].id`   | `integer`       |      |
| `data[].name` | `string`        |      |

---

### 8.20 获取关键岗位人员类别字典

| 项          | 内容                                                |
| ----------- | --------------------------------------------------- |
| 接口路径    | `/person/getKeyPositionPersonCategoryList`          |
| 请求方法    | `GET`                                               |
| 前端封装    | `SystemController.getKeyPositionPersonCategoryList` |
| Swagger Tag | personnelApi                                        |
| 作用说明    | 获取关键岗位人员类别字典                            |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段          | 类型            | 说明 |
| ------------- | --------------- | ---- |
| `code`        | `integer`       |      |
| `message`     | `string`        |      |
| `data`        | `array<object>` |      |
| `data[].id`   | `integer`       |      |
| `data[].name` | `string`        |      |

---

### 8.21 获取证件类型字典

| 项          | 内容                                      |
| ----------- | ----------------------------------------- |
| 接口路径    | `/person/getCertificateTypeList`          |
| 请求方法    | `GET`                                     |
| 前端封装    | `SystemController.getCertificateTypeList` |
| Swagger Tag | personnelApi                              |
| 作用说明    | 获取证件类型字典                          |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段          | 类型            | 说明 |
| ------------- | --------------- | ---- |
| `code`        | `integer`       |      |
| `message`     | `string`        |      |
| `data`        | `array<object>` |      |
| `data[].id`   | `integer`       |      |
| `data[].name` | `string`        |      |

---

### 8.22 获取技术等级字典

| 项          | 内容                                     |
| ----------- | ---------------------------------------- |
| 接口路径    | `/person/getTechnicalLevelList`          |
| 请求方法    | `GET`                                    |
| 前端封装    | `SystemController.getTechnicalLevelList` |
| Swagger Tag | personnelApi                             |
| 作用说明    | 获取技术等级字典                         |

**请求参数（Body）：**

_无明确请求体字段（可能为 Query/Path 参数、空 Body，或 Schema 未展开）。_

**响应体：**

| 字段          | 类型            | 说明 |
| ------------- | --------------- | ---- |
| `code`        | `integer`       |      |
| `message`     | `string`        |      |
| `data`        | `array<object>` |      |
| `data[].id`   | `integer`       |      |
| `data[].name` | `string`        |      |

---
