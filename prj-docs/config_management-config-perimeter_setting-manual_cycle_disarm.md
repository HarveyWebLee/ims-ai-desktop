# 手动撤布防（manual_cycle_disarm）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                                       |
| ------------------ | -------------------------------------------------------------------------- |
| 模块名称（中文）   | 手动撤布防                                                                 |
| 模块名称（英文）   | Manual Cycle Disarm                                                        |
| 所属 Group（中文） | 周界防区设定                                                               |
| 所属 Group（英文） | Perimeter Zone Setting                                                     |
| Group ID           | `perimeter_setting`                                                        |
| 菜单位置           | 配置管理平台 → 配置管理 → 周界防区设定 → 手动撤布防                        |
| 路由路径           | `/config_management/config/manual_cycle_disarm`                            |
| 页面目录           | `src/pages/config_management/config/perimeter_setting/manual_cycle_disarm` |

## 1. 模块定位与项目作用

手动周期撤防是综合信息平台中「周界防区设定」业务域下的功能模块，对应页面目录 `src/pages/config_management/config/perimeter_setting/manual_cycle_disarm`。

在项目中的主要作用：

- 作为「配置管理平台 → 配置管理 → 周界防区设定 → 手动周期撤防」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
- 通过本模块维护或消费的数据，可能被同业务域其他页面、报表、组态或流程能力引用。
- 具体能力以页面交互与接口清单为准；变更本模块配置/数据时，应评估对上下游模块的影响。

---

## 3. 属性字段说明

以下字段由页面代码启发式提取，用于快速了解主数据形态；若与线上表单不一致，以实际页面与接口契约为准。

| 字段名            | 中文含义            | 作用说明                        |
| ----------------- | ------------------- | ------------------------------- |
| deviceName        | currentStatus       | 模块表单/列表字段，详见页面配置 |
| defenceStatusName | defenceStatusCheck  | 模块表单/列表字段，详见页面配置 |
| areaId            | defenceArea         | 模块表单/列表字段，详见页面配置 |
| defenceAreaId     | defenceArea         | 模块表单/列表字段，详见页面配置 |
| onlineStatus      | currentStatus       | 模块表单/列表字段，详见页面配置 |
| defenceStatus     | defenceAreaStatus   | 模块表单/列表字段，详见页面配置 |
| validStatusName   | defenceStatusCheck  | 模块表单/列表字段，详见页面配置 |
| manual_setting    | manualSetting       | 模块表单/列表字段，详见页面配置 |
| modelType         | modeSwitch          | 模块表单/列表字段，详见页面配置 |
| defence_cycle     | defenceCycleSetting | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

---

- 复制

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                      | 关系说明 |
| ----------------------------- | -------- |
| 撤防记录（evacuation_record） | 同组     |
| 防区分组（group）             | 同组     |
| 维护（maintenance）           | 同组     |

### 5.2 上游依赖 / 下游消费

- **上游**：用户及参数管理（`user`）、基础数据（`basedata`）。

---
