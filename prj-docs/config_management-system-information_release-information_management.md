# 信息管理（information_management）知识库

## 0. 路由与归属信息

| 项                 | 内容                                                                            |
| ------------------ | ------------------------------------------------------------------------------- |
| 模块名称（中文）   | 信息管理                                                                        |
| 模块名称（英文）   | information_management                                                          |
| 所属 Group（中文） | 信息发布                                                                        |
| 所属 Group（英文） | Information Release                                                             |
| Group ID           | `information_release`                                                           |
| 菜单位置           | 配置管理平台 → 系统管理 → 信息发布 → 信息管理                                   |
| 路由路径           | `/config_management/system/information_management`                              |
| 页面目录           | `src/pages/config_management/system/information_release/information_management` |

## 1. 模块定位与项目作用

信息管理是综合信息平台「信息发布」下的功能页面。

## 3. 功能清单

- 以实际页面按钮与表单为准

## 4. 与其他功能模块的关系

- 同属模块索引：[information_release.md](./information_release.md)
- 上游主要为登录会话与菜单授权（用户及参数管理）。

## 5. 关键业务规则与注意事项

1. 操作前确认具备对应菜单与按钮权限。
2. 接口入参以 Swagger 与前端封装为准。

## 6. 总结

本模块（`information_management`）归属「信息发布」，路由 `/config_management/system/information_management`。
