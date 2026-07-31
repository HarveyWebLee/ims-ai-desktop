/**
 * 将 App.useApp() 实例绑定到 feedback 模块，供非组件代码使用
 * 同步绑定（非 useEffect），避免首屏 toast 在 effect 前丢失
 */
import { App } from "antd";
import { bindAntdAppApis } from "./feedback";

export default function AntdAppBridge() {
  const apis = App.useApp();
  bindAntdAppApis(apis);
  return null;
}
