# 事件流配置（event_flow_config）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                                |
| ------------------ | ------------------------------------------------------------------- |
| 模块名称（中文）   | 事件流配置                                                          |
| 模块名称（英文）   | Event Flow Config                                                   |
| 所属 Group（中文） | 事件配置                                                            |
| 所属 Group（英文） | Event Config                                                        |
| Group ID           | `event_config`                                                      |
| 菜单位置           | 配置管理平台 → 配置管理 → 事件配置 → 事件流配置                     |
| 路由路径           | `/config_management/config/event_flow_config`                       |
| 页面目录           | `src/pages/config_management/config/event_config/event_flow_config` |

## 1. 模块定位与项目作用

事件流程配置是综合信息平台中「事件配置」业务域下的功能模块，对应页面目录 `src/pages/config_management/config/event_config/event_flow_config`。

在项目中的主要作用：

- 作为「配置管理平台 → 配置管理 → 事件配置 → 事件流程配置」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
- 通过本模块维护或消费的数据，可能被同业务域其他页面、报表、组态或流程能力引用。
- 具体能力以页面交互与接口清单为准；变更本模块配置/数据时，应评估对上下游模块的影响。

---

## 3. 属性字段说明

以下字段由页面代码启发式提取，用于快速了解主数据形态；若与线上表单不一致，以实际页面与接口契约为准。

| 字段名        | 中文含义                              | 作用说明                        |
| ------------- | ------------------------------------- | ------------------------------- |
| currVersionId | 备注                                  | 模块表单/列表字段，详见页面配置 |
| flowCode      | 流程编码                              | 模块表单/列表字段，详见页面配置 |
| flowName      | 流程名称                              | 模块表单/列表字段，详见页面配置 |
| flowType      | 流程类型                              | 模块表单/列表字段，详见页面配置 |
| sourceCode    | 来源编码                              | 模块表单/列表字段，详见页面配置 |
| status        | 状态                                  | 模块表单/列表字段，详见页面配置 |
| flowJson      | 流程配置                              | 模块表单/列表字段，详见页面配置 |
| remark        | 备注                                  | 模块表单/列表字段，详见页面配置 |
| id            | eventFlowConfig.snapshotVersionColumn | 模块表单/列表字段，详见页面配置 |
| flowVersion   | eventFlowConfig.snapshotRemarkColumn  | 模块表单/列表字段，详见页面配置 |
| versionStatus | eventFlowConfig.versionStatus         | 模块表单/列表字段，详见页面配置 |
| createTime    | eventFlowConfig.createTime            | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

---

- 复制
- 分页查询

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                                         | 关系说明 |
| ------------------------------------------------ | -------- |
| 周期事件配置（cycle_event_config）               | 同组     |
| 事件执行记录（event_execution_record）           | 同组     |
| 事件联动规则（event_link_rule）                  | 同组     |
| 事件联动规则（高级）（event_link_rule_advanced） | 同组     |
| 事件规则记录（event_rule_record）                | 同组     |

### 5.2 上游依赖 / 下游消费

- **上游**：用户及参数管理（`user`）、基础数据（`basedata`）。

---
