# 通信网关（communication_config）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                                              |
| ------------------ | --------------------------------------------------------------------------------- |
| 模块名称（中文）   | 通信网关                                                                          |
| 模块名称（英文）   | Communication Config                                                              |
| 所属 Group（中文） | 数采服务器                                                                        |
| 所属 Group（英文） | Data Acquisition Server                                                           |
| Group ID           | `data_acquisition_server`                                                         |
| 菜单位置           | 配置管理平台 → 配置管理 → 数采服务器 → 通信网关                                   |
| 路由路径           | `/config_management/config/communication_config`                                  |
| 页面目录           | `src/pages/config_management/config/data_acquisition_server/communication_config` |

## 1. 模块定位与项目作用

通信配置是综合信息平台中「数采服务器」业务域下的功能模块，对应页面目录 `src/pages/config_management/config/data_acquisition_server/communication_config`。

在项目中的主要作用：

- 作为「配置管理平台 → 配置管理 → 数采服务器 → 通信配置」菜单下的业务入口，承载该场景的数据维护、查询或运维操作。
- 通过本模块维护或消费的数据，可能被同业务域其他页面、报表、组态或流程能力引用。
- 具体能力以页面交互与接口清单为准；变更本模块配置/数据时，应评估对上下游模块的影响。

---

## 3. 属性字段说明

以下字段由页面代码启发式提取，用于快速了解主数据形态；若与线上表单不一致，以实际页面与接口契约为准。

| 字段名               | 中文含义       | 作用说明                        |
| -------------------- | -------------- | ------------------------------- |
| subSystemName        | 所属区域       | 模块表单/列表字段，详见页面配置 |
| regionName           | 设备名称       | 模块表单/列表字段，详见页面配置 |
| manufacturer         | 规格型号       | 模块表单/列表字段，详见页面配置 |
| id                   | 主键ID         | 模块表单/列表字段，详见页面配置 |
| deviceGroupId        | 设备分组       | 模块表单/列表字段，详见页面配置 |
| deviceGroupName      | 设备分组       | 模块表单/列表字段，详见页面配置 |
| subSystemId          | 所属子系统     | 模块表单/列表字段，详见页面配置 |
| deviceName           | 设备名称       | 模块表单/列表字段，详见页面配置 |
| deviceCode           | 设备编号       | 模块表单/列表字段，详见页面配置 |
| deviceStatus         | 设备启用状态   | 模块表单/列表字段，详见页面配置 |
| alertInterval        | 告警间隔(分钟) | 模块表单/列表字段，详见页面配置 |
| onlineStatus         | 设备在线状态   | 模块表单/列表字段，详见页面配置 |
| onlineStatusName     | 设备在线状态   | 模块表单/列表字段，详见页面配置 |
| regionId             | 所属区域       | 模块表单/列表字段，详见页面配置 |
| commModel            | 通信模式       | 模块表单/列表字段，详见页面配置 |
| collectServerId      | 代理设备       | 模块表单/列表字段，详见页面配置 |
| collectServerName    | 代理设备       | 模块表单/列表字段，详见页面配置 |
| deviceCategoryId     | 监控设备类型   | 模块表单/列表字段，详见页面配置 |
| deviceCategoryName   | 监控设备类型   | 模块表单/列表字段，详见页面配置 |
| model                | 规格型号       | 模块表单/列表字段，详见页面配置 |
| ipAddress            | IP地址         | 模块表单/列表字段，详见页面配置 |
| location             | 所在位置       | 模块表单/列表字段，详见页面配置 |
| firstUseTime         | 首次使用时间   | 模块表单/列表字段，详见页面配置 |
| remark               | 备注           | 模块表单/列表字段，详见页面配置 |
| devicePic            | 照片           | 模块表单/列表字段，详见页面配置 |
| maintenanceSituation | 保养情况       | 模块表单/列表字段，详见页面配置 |
| repairSituation      | 检修情况       | 模块表单/列表字段，详见页面配置 |
| protocolId           | 通讯协议       | 模块表单/列表字段，详见页面配置 |
| protocolName         | 通讯协议       | 模块表单/列表字段，详见页面配置 |
| protocolParams       | 协议参数       | 模块表单/列表字段，详见页面配置 |
| file                 | file           | 模块表单/列表字段，详见页面配置 |
| 图片                 | 图片           | 模块表单/列表字段，详见页面配置 |

---

## 4. 功能清单

---

- 批量修改导入
- 复制

## 5. 与其他功能模块的关系

### 5.1 同目录兄弟模块

| 关联模块                      | 关系说明 |
| ----------------------------- | -------- |
| 数采服务器（das）             | 同组     |
| 服务组件（service_component） | 同组     |

### 5.2 上游依赖 / 下游消费

- **上游**：监控设备（`monitor_equipment`）、用户及参数管理（`user`）、基础数据（`basedata`）。

---
