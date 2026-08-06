# GoBinding（go_binding）知识库

## 0. 路由与归属信息

| 项                 | 内容                   |
| ------------------ | ---------------------- |
| 模块名称（中文）   | GoBinding              |
| 模块名称（英文）   | Go Binding             |
| 所属 Group（中文） | GoBinding              |
| 所属 Group（英文） | Go Binding             |
| Group ID           | `go_binding`           |
| 菜单位置           | GoBinding              |
| 路由路径           | `/go_binding`          |
| 页面目录           | `src/pages/go_binding` |

## 1. 模块定位与项目作用

GoBinding是综合信息平台中「GoBinding」业务域下的功能模块，对应页面目录 `src/pages/go_binding`。

在项目中的主要作用：

- 作为「GoBinding」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
- 通过本模块维护或消费的数据，可能被同业务域其他页面、报表、组态或流程能力引用。
- 具体能力以页面交互与接口清单为准；变更本模块配置/数据时，应评估对上下游模块的影响。

---

## 4. 与其他功能模块的关系

### 4.1 相关模块

| 关联模块           | 文档                                             | 关系说明               |
| ------------------ | ------------------------------------------------ | ---------------------- |
| 页面运行           | [page.md](./page.md)                             | 绑定结果用于运行态页面 |
| 设备变量           | [device_variable.md](./device_variable.md)       | 绑定点位来源           |
| HMI WebSocket 测试 | [hmi_websocket_test.md](./hmi_websocket_test.md) | 联调辅助页             |

### 4.2 上游依赖 / 下游消费

- **上游**：用户及参数管理（`user`）。
- **下游**：HMI/页面运行绑定。
