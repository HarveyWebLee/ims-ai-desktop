# 动用使用（usage）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                                            |
| ------------------ | ------------------------------------------------------------------------------- |
| 模块名称（中文）   | 动用使用                                                                        |
| 模块名称（英文）   | Usage                                                                           |
| 所属 Group（中文） | 设施设备管理                                                                    |
| 所属 Group（英文） | Facilities and Equipment Management                                             |
| Group ID           | `facilities_management`                                                         |
| 菜单位置           | 配置管理平台 → 阵地维护管理 → 设施设备管理 → 动用使用                           |
| 路由路径           | `/config_management/positional_management/usage`                                |
| 页面目录           | `src/pages/config_management/positional_management/facilities_management/usage` |

## 1. 模块定位与项目作用

使用是综合信息平台中「设施设备管理」业务域下的功能模块，对应页面目录 `src/pages/config_management/positional_management/facilities_management/usage`。

在项目中的主要作用：

- 作为「配置管理平台 → 阵地维护管理 → 设施设备管理 → 使用」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
- 通过本模块维护或消费的数据，可能被同业务域其他页面、报表、组态或流程能力引用。
- 具体能力以页面交互与接口清单为准；变更本模块配置/数据时，应评估对上下游模块的影响。

---

## 3. 属性字段说明

以下字段由页面代码启发式提取，用于快速了解主数据形态；若与线上表单不一致，以实际页面与接口契约为准。

| 字段名             | 中文含义                    | 作用说明                        |
| ------------------ | --------------------------- | ------------------------------- |
| runDevVarName      | 运行设备变量编码            | 模块表单/列表字段，详见页面配置 |
| runDevVarCode      | 设施设备编码                | 模块表单/列表字段，详见页面配置 |
| ctrlDevVarName     | 控制设备变量编码            | 模块表单/列表字段，详见页面配置 |
| ctrlDevVarCode     | 上次保养时间                | 模块表单/列表字段，详见页面配置 |
| runDeviceVar       | 运行设备及变量              | 模块表单/列表字段，详见页面配置 |
| ctrlDeviceVar      | 控制设备及变量              | 模块表单/列表字段，详见页面配置 |
| modelConfig        | 模式配置                    | 模块表单/列表字段，详见页面配置 |
| deviceCategoryId   | 设备类别                    | 模块表单/列表字段，详见页面配置 |
| runDevName         | 运行设备名称                | 模块表单/列表字段，详见页面配置 |
| runDevCode         | 运行设备编码                | 模块表单/列表字段，详见页面配置 |
| facilityDeviceCode | 设施设备编码                | 模块表单/列表字段，详见页面配置 |
| totalTime          | 累计运行时间                | 模块表单/列表字段，详见页面配置 |
| ctrlDevName        | 控制设备名称                | 模块表单/列表字段，详见页面配置 |
| ctrlDevCode        | 控制设备编码                | 模块表单/列表字段，详见页面配置 |
| lastUpkeepTime     | 上次保养时间                | 模块表单/列表字段，详见页面配置 |
| runTime            | 自上次保养运行时间          | 模块表单/列表字段，详见页面配置 |
| status             | 启用状态                    | 模块表单/列表字段，详见页面配置 |
| modelName          | usageManagement.deviceName  | 模块表单/列表字段，详见页面配置 |
| dcn                | usageManagement.deviceCode  | 模块表单/列表字段，详见页面配置 |
| dn                 | usageManagement.varName     | 模块表单/列表字段，详见页面配置 |
| vcn                | usageManagement.varCode     | 模块表单/列表字段，详见页面配置 |
| vn                 | usageManagement.varValue    | 模块表单/列表字段，详见页面配置 |
| vv                 | usageManagement.runDuration | 模块表单/列表字段，详见页面配置 |
| useTime            | usageManagement.runDuration | 模块表单/列表字段，详见页面配置 |
| JSON导入           | JSON导入                    | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

---

- 复制
- 分页查询

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                                    | 关系说明 |
| ------------------------------------------- | -------- |
| 属性字典（attribute_dictionary）            | 同组     |
| 分类管理（category_management）             | 同组     |
| 设施管理（facility_management）             | 同组     |
| 交接管理（handover_management）             | 同组     |
| 安装位置管理（install_position_management） | 同组     |
| 质量统计（quality_statistics）              | 同组     |

### 5.2 上游依赖 / 下游消费

- **上游**：监控设备（`monitor_equipment`）、用户及参数管理（`user`）、基础数据（`basedata`）。

---
