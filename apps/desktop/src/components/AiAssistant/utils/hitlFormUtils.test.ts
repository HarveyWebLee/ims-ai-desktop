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

  it("strips empty multi-select placeholders from current", () => {
    const values = buildHitlInitialValues({
      fields: [
        {
          name: "alarm_category_id",
          label: "报警类型",
          type: "async_select",
          mode: "multiple",
        },
        {
          name: "alarm_rank_id",
          label: "报警级别",
          type: "async_select",
          mode: "multiple",
        },
        {
          name: "status",
          label: "报警状态",
          type: "select",
          mode: "multiple",
          options: [{ label: "待确认", value: "1" }],
        },
        { name: "device_name", label: "设备名称", type: "text" },
      ],
      current: {
        device_name: "岗亭-1",
        status: "",
        alarm_category_id: [""],
        alarm_rank_id: "",
      },
    });
    expect(values).toEqual({ device_name: "岗亭-1" });
  });

  it("normalizes multi-select string to array", () => {
    const values = buildHitlInitialValues({
      fields: [
        {
          name: "status",
          label: "报警状态",
          type: "select",
          mode: "multiple",
          options: [{ label: "待确认", value: "1" }],
        },
      ],
      current: { status: "1" },
    });
    expect(values.status).toEqual(["1"]);
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
