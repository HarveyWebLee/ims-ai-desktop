/**
 * HITL 表单值规范化：datetime_range 等复合字段 → resume 参数字典
 */
import type { HitlField, HitlPayload } from "@ims/shared-types";

export interface HitlDateTimeRangeValue {
  start_time?: string;
  end_time?: string;
}

function hasMeaningfulValue(value: unknown): boolean {
  if (value == null) return false;
  if (typeof value === "string") return value.trim().length > 0;
  if (Array.isArray(value)) {
    return value.some((item) => String(item ?? "").trim().length > 0);
  }
  if (typeof value === "object") {
    return Object.keys(value as Record<string, unknown>).length > 0;
  }
  return true;
}

/** 多选字段：去掉空项；单字符串升为单元素数组；全空则省略 */
function normalizeMultiSelectInitial(value: unknown): string[] | undefined {
  if (value == null) return undefined;
  const raw = Array.isArray(value) ? value : [value];
  const items = raw.map((item) => String(item ?? "").trim()).filter(Boolean);
  return items.length > 0 ? items : undefined;
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
 * 多选字段会剔除 "" / [""]，避免 Select 出现空白已选项。
 */
export function buildHitlInitialValues(
  payload: Pick<HitlPayload, "fields" | "current">,
): Record<string, unknown> {
  const current = payload.current;
  if (!current || typeof current !== "object") return {};

  const out: Record<string, unknown> = { ...current };
  const fields = payload.fields ?? [];

  for (const field of fields) {
    const isMultiSelect =
      field.mode === "multiple" && (field.type === "select" || field.type === "async_select");
    if (!isMultiSelect) continue;
    const normalized = normalizeMultiSelectInitial(out[field.name]);
    if (normalized) {
      out[field.name] = normalized;
    } else {
      delete out[field.name];
    }
  }

  for (const field of fields) {
    if (field.type !== "datetime_range") continue;
    const existing = out[field.name];
    if (existing && typeof existing === "object") continue;
    const start = typeof out.start_time === "string" ? out.start_time : undefined;
    const end = typeof out.end_time === "string" ? out.end_time : undefined;
    if (start || end) {
      out[field.name] = { start_time: start, end_time: end };
    }
  }

  // 去掉其余无意义空值（如 status: ""），防止非多选控件被空串污染
  for (const [key, value] of Object.entries(out)) {
    if (!hasMeaningfulValue(value)) {
      delete out[key];
    }
  }

  return out;
}
