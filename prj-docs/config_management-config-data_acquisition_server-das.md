# 数采服务器（das）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                             |
| ------------------ | ---------------------------------------------------------------- |
| 模块名称（中文）   | 数采服务器                                                       |
| 模块名称（英文）   | Data Acquisition Server                                          |
| 所属 Group（中文） | 数采服务器                                                       |
| 所属 Group（英文） | Data Acquisition Server                                          |
| Group ID           | `data_acquisition_server`                                        |
| 菜单位置           | 配置管理平台 → 配置管理 → 数采服务器 → 数采服务器                |
| 路由路径           | `/config_management/config/das`                                  |
| 页面目录           | `src/pages/config_management/config/data_acquisition_server/das` |

## 1. 模块定位与项目作用

数采服务器是综合信息平台中「数采服务器」业务域下的功能模块，对应页面目录 `src/pages/config_management/config/data_acquisition_server/das`。

在项目中的主要作用：

- 作为「配置管理平台 → 配置管理 → 数采服务器」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
- 通过本模块维护或消费的数据，可能被同业务域其他页面、报表、组态或流程能力引用。
- 具体能力以页面交互与接口清单为准；变更本模块配置/数据时，应评估对上下游模块的影响。

---

## 3. 属性字段说明

以下字段由页面代码启发式提取，用于快速了解主数据形态；若与线上表单不一致，以实际页面与接口契约为准。

| 字段名                 | 中文含义               | 作用说明                        |
| ---------------------- | ---------------------- | ------------------------------- |
| id                     | serverNameLabel        | 模块表单/列表字段，详见页面配置 |
| label                  | serverNowTime          | 模块表单/列表字段，详见页面配置 |
| serverName             | serverNameLabel        | 模块表单/列表字段，详见页面配置 |
| onlineStatus           | onlineStatus           | 模块表单/列表字段，详见页面配置 |
| runStatus              | businessStatus         | 模块表单/列表字段，详见页面配置 |
| version                | version                | 模块表单/列表字段，详见页面配置 |
| serverNowTime          | serverNowTime          | 模块表单/列表字段，详见页面配置 |
| remark                 | remark                 | 模块表单/列表字段，详见页面配置 |
| serverIp               | serverIp               | 模块表单/列表字段，详见页面配置 |
| batchUpdateIp          | batchUpdateIp          | 模块表单/列表字段，详见页面配置 |
| downloadDistributedLog | downloadDistributedLog | 模块表单/列表字段，详见页面配置 |
| downloadStackInfo      | downloadStackInfo      | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

---

- 批量修改导入

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                         | 关系说明 |
| -------------------------------- | -------- |
| 通信配置（communication_config） | 同组     |
| 服务组件（service_component）    | 同组     |

### 5.2 上游依赖 / 下游消费

- **上游**：用户及参数管理（`user`）。

---
