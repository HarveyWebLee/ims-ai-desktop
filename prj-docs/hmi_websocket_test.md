# HMI WebSocket 测试（hmi_websocket_test）知识库

## 0. 路由与归属信息

| 项                 | 内容                           |
| ------------------ | ------------------------------ |
| 模块名称（中文）   | HMI WebSocket 测试             |
| 模块名称（英文）   | HMI WebSocket Test             |
| 所属 Group（中文） | HMI WebSocket 测试             |
| 所属 Group（英文） | HMI WebSocket Test             |
| Group ID           | `hmi_websocket_test`           |
| 菜单位置           | HMI WebSocket 测试             |
| 路由路径           | `/hmi_websocket_test`          |
| 页面目录           | `src/pages/hmi_websocket_test` |

## 1. 模块定位与项目作用

HMI WebSocket 测试是综合信息平台中「HMI WebSocket 测试」业务域下的功能模块，对应页面目录 `src/pages/hmi_websocket_test`。

在项目中的主要作用：

- 作为「HMI WebSocket 测试」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
- 通过本模块维护或消费的数据，可能被同业务域其他页面、报表、组态或流程能力引用。
- 具体能力以页面交互与接口清单为准；变更本模块配置/数据时，应评估对上下游模块的影响。

---

## 3. 属性字段说明

以下字段由页面代码启发式提取，用于快速了解主数据形态；若与线上表单不一致，以实际页面与接口契约为准。

| 字段名               | 中文含义                            | 作用说明                        |
| -------------------- | ----------------------------------- | ------------------------------- |
| id                   | hmiWebsocketTestColumnId            | 模块表单/列表字段，详见页面配置 |
| status               | hmiWebsocketTestColumnStatus        | 模块表单/列表字段，详见页面配置 |
| createTime           | hmiWebsocketTestColumnCreateTime    | 模块表单/列表字段，详见页面配置 |
| firstDataTime        | hmiWebsocketTestColumnFirstDataTime | 模块表单/列表字段，详见页面配置 |
| timeDiff             | hmiWebsocketTestColumnTimeDiff      | 模块表单/列表字段，详见页面配置 |
| connectionStatusInfo | hmiWebsocketTestColumnStatusInfo    | 模块表单/列表字段，详见页面配置 |
| errorMessage         | hmiWebsocketTestColumnErrorMessage  | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

---

- 实时监视/WebSocket
- 分页查询

## 5. 与其他功能模块的关系

### 5.1 相关模块

| 关联模块  | 文档                                       | 关系说明       |
| --------- | ------------------------------------------ | -------------- |
| 页面运行  | [page.md](./page.md)                       | 正式运行态入口 |
| GoBinding | [go_binding.md](./go_binding.md)           | 绑定调试相关   |
| 设备变量  | [device_variable.md](./device_variable.md) | 推送/订阅点位  |

### 5.2 上游依赖 / 下游消费

- **上游**：用户及参数管理（`user`）。
- **下游**：仅用于联调测试，非正式业务菜单。
