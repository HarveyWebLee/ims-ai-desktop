/**
 * AI 助手批量确认/处理告警后，通知主内容区刷新告警列表（避免整页 reload）
 */
export const ALARM_DATA_CHANGED_EVENT = "ims:alarm-data-changed";

/** 派发告警数据变更事件，供报警查询页等订阅 */
export function dispatchAlarmDataChanged(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent(ALARM_DATA_CHANGED_EVENT));
}

/** 订阅告警数据变更；返回取消订阅函数 */
export function subscribeAlarmDataChanged(handler: () => void): () => void {
  if (typeof window === "undefined") return () => undefined;
  window.addEventListener(ALARM_DATA_CHANGED_EVENT, handler);
  return () => window.removeEventListener(ALARM_DATA_CHANGED_EVENT, handler);
}
