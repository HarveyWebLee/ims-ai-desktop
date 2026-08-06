/**
 * HITL 表单值规范化：datetime_range 等复合字段 → resume 参数字典
 */
import type { HitlField, HitlPayload } from "@ims/shared-types";

export interface HitlDateTimeRangeValue {
  start_time?: string;
  end_time?: string;
}

/** 提交前将表单值转为后端工具可识别的 flat 参数 */
export function normalizeHitlFormValues(
  values: Record<string, unknown>,
  fields: HitlField[] | undefined,
): Record<string, unknown> {
  const out: Record<string, unknown> = { ...values };

  for (const field of fields ?? []) {
    if (field.type !== "datetime_range") continue;
    const range = out[field.name] as HitlDateTimeRangeValue | undefined;
    if (range?.start_time) {
      out.start_time = range.start_time;
    }
    if (range?.end_time) {
      out.end_time = range.end_time;
    }
    delete out[field.name];
  }

  return out;
}

/**
 * 将 interrupt.current（flat）转为 Form initialValues。
 * datetime_range 字段需要 { start_time, end_time } 结构。
 */
export function buildHitlInitialValues(
  payload: Pick<HitlPayload, "fields" | "current">,
): Record<string, unknown> {
  const current = payload.current;
  if (!current || typeof current !== "object") return {};

  const out: Record<string, unknown> = { ...current };
  for (const field of payload.fields ?? []) {
    if (field.type !== "datetime_range") continue;
    const existing = out[field.name];
    if (existing && typeof existing === "object") continue;
    const start = typeof out.start_time === "string" ? out.start_time : undefined;
    const end = typeof out.end_time === "string" ? out.end_time : undefined;
    if (start || end) {
      out[field.name] = { start_time: start, end_time: end };
    }
  }
  return out;
}
