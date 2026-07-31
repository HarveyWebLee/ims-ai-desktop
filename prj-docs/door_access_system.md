# 门禁系统

> 英文名：Door Access System  
> 模块 ID：`door_access_system`  
> 所属业务域：系统管理（`/config_management/system`）  
> 来源：平台功能模块知识库（本仓 `prj-docs`）

## 模块说明

门禁信息同步、值班、安全检查、岗哨交接、出入库与出入信息管理统计。

## 适用场景

账号权限、基础主数据、日志审计、门禁业务与信息发布等系统级管理场景。

## 功能页面

| 页面         | 路径                             | 路由                                                       | 说明                             |
| ------------ | -------------------------------- | ---------------------------------------------------------- | -------------------------------- |
| 门禁信息同步 | `door_access_sync`               | `/config_management/system/door_access_sync`               | 同步门禁系统人员/卡/权限等信息。 |
| 值班信息     | `duty_info`                      | `/config_management/system/duty_info`                      | 门禁侧值班信息。                 |
| 安全检查     | `safety_check`                   | `/config_management/system/safety_check`                   | 安全检查记录。                   |
| 岗哨交接     | `guard_post_handover`            | `/config_management/system/guard_post_handover`            | 岗哨交接班。                     |
| 出入库管理   | `inner_storage`                  | `/config_management/system/inner_storage`                  | 出入库业务管理。                 |
| 出入信息管理 | `in_out_storage`                 | `/config_management/system/in_out_storage`                 | 出入信息管理。                   |
| 出入信息维护 | `access_information_maintenance` | `/config_management/system/access_information_maintenance` | 出入信息维护。                   |
| 出入信息统计 | `access_statistics`              | `/config_management/system/access_statistics`              | 出入信息统计。                   |

## 操作指引（通用）

1. 登录综合信息管理平台，从门户进入「配置管理平台」。
2. 打开左侧「系统管理」→「门禁系统」。
3. 在列表页按条件查询；通过新增/编辑/删除维护数据（具体按钮以页面为准）。
4. 若页面含树形筛选（区域/组织/类别），先选节点再操作右侧列表。
5. 无菜单权限时，请管理员在「角色授权 / 菜单管理」中分配。

## 关联依赖

依赖基础数据中的岗哨、访问组及门禁同步。

## 常见问题

- **看不到本模块菜单**：检查账号角色是否授权；超级管理员可在「菜单管理 / 角色授权 / 场景管理」配置。
- **列表无数据**：确认筛选条件、所属区域/组织节点，以及后端服务与数据权限范围。
- **无法保存**：检查必填项、字典引用是否存在，以及是否具备写权限。

## 代码定位

- 功能分组：`groupId: door_access_system`
- 对应平台配置管理功能页面
