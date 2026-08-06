import { describe, expect, it } from "vitest";
import { buildHitlInitialValues, normalizeHitlFormValues } from "./hitlFormUtils";

describe("buildHitlInitialValues", () => {
  it("maps flat start/end into datetime_range field", () => {
    const values = buildHitlInitialValues({
      fields: [{ name: "time_range", label: "时间", type: "datetime_range" }],
      current: {
        start_time: "2026-01-01 00:00:00",
        end_time: "2026-01-02 00:00:00",
        device_code: "zhonglian_9001",
      },
    });
    expect(values.device_code).toBe("zhonglian_9001");
    expect(values.time_range).toEqual({
      start_time: "2026-01-01 00:00:00",
      end_time: "2026-01-02 00:00:00",
    });
  });

  it("returns empty object without current", () => {
    expect(buildHitlInitialValues({ fields: [], current: undefined })).toEqual({});
  });
});

describe("normalizeHitlFormValues", () => {
  it("flattens datetime_range on submit", () => {
    const out = normalizeHitlFormValues(
      {
        time_range: {
          start_time: "2026-01-01 00:00:00",
          end_time: "2026-01-02 00:00:00",
        },
        device_code: "D1",
      },
      [{ name: "time_range", label: "时间", type: "datetime_range" }],
    );
    expect(out.start_time).toBe("2026-01-01 00:00:00");
    expect(out.end_time).toBe("2026-01-02 00:00:00");
    expect(out.time_range).toBeUndefined();
    expect(out.device_code).toBe("D1");
  });
});
