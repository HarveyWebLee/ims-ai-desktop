/**
 * @ims/agent-core — 平台页面导航路由规范（navigate_to 唯一数据源）
 *
 * originPath 规则与平台配置管理路由一致。
 * 清单权威数据：services/platform-agent-service/app/data/navigation_routes.json。
 */

/** 路由路径规范（写入 Agent 系统提示词） */
export const ROUTE_ORIGIN_PATH_RULES = `## 平台路由路径规范（navigate_to 必须遵守）

1. **只使用 originPath（浏览器地址栏路径）**，禁止使用组件 filePath。
2. **originPath 不含 groupId**：\`meta.groupId\` 仅用于前端组件懒加载目录，不出现在 URL 中。
   - 错误：\`/config_management/config/monitor_equipment/equipment_manage\`（含 groupId）
   - 正确：\`/config_management/config/equipment_manage\`
3. **拼接规则**（与平台路由拼接规则一致）：
   - 顶层：\`path\` 以 \`/\` 开头时即为 originPath（如 \`/overview\`）
   - 子级：\`父级 originPath + '/' + 当前 path\`（如 \`equipment_manage\` → \`/config_management/config/equipment_manage\`）
4. **优先使用运行时注入的「常用页面路由」速查表**；\`path\` 传使用者原话，由工具模糊匹配。
5. **禁止**编造未在速查表中的简写路径。
6. **设施管理** ≠ **设备管理**（不同页面，禁止混淆）。`;

/** 导航条目（与导出的 navigation_routes.json 结构一致） */
export interface NavigationRouteEntry {
  /** 菜单中文名 */
  name: string;
  /** 浏览器 originPath */
  path: string;
  /** 侧边栏分组（仅说明用，不在 URL 中） */
  group?: string;
  /** 组件目录分组 id（仅 filePath 用，禁止写入 navigate path） */
  groupId?: string;
}

export interface NavigationRoutesManifest {
  generatedAt: string;
  rules: string;
  routes: NavigationRouteEntry[];
  /** 错误 path / 中文别名 → 正确 originPath */
  aliases: Record<string, string>;
}
