/**
 * antd App 静态反馈桥接（message / notification / modal）
 *
 * 官方推荐：组件内优先 `App.useApp()`；
 * 非 React 树（工具类、部分 hook）经本模块转发，以继承 ConfigProvider 主题与上下文。
 *
 * @see https://ant.design/components/app
 */
import type { MessageInstance } from "antd/es/message/interface";
import type { NotificationInstance } from "antd/es/notification/interface";
import type { ModalStaticFunctions } from "antd/es/modal/confirm";

type ModalApi = Omit<ModalStaticFunctions, "warn">;

let messageApi: MessageInstance | null = null;
let notificationApi: NotificationInstance | null = null;
let modalApi: ModalApi | null = null;

export function bindAntdAppApis(apis: {
  message: MessageInstance;
  notification: NotificationInstance;
  modal: ModalApi;
}): void {
  messageApi = apis.message;
  notificationApi = apis.notification;
  modalApi = apis.modal;
}

function unboundWarn(kind: string): void {
  if (import.meta.env.DEV) {
    console.warn(`[antd] ${kind} API 尚未绑定：确认 <AntdAppBridge /> 已挂在 <App> 内`);
  }
}

function createProxy<T extends object>(getApi: () => T | null, kind: string): T {
  return new Proxy({} as T, {
    get(_target, prop, receiver) {
      const api = getApi();
      if (!api) {
        unboundWarn(kind);
        return () => undefined;
      }
      const value = Reflect.get(api, prop, receiver);
      return typeof value === "function" ? value.bind(api) : value;
    },
  });
}

/** 全局 message（须在 AntApp 挂载后使用） */
export const message = createProxy(() => messageApi, "message");

/** 全局 notification */
export const notification = createProxy(() => notificationApi, "notification");

/** 全局 modal 静态方法 */
export const modal = createProxy(() => modalApi, "modal");
