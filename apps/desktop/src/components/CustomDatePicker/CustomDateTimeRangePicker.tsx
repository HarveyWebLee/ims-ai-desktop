import { DatePicker } from "antd";
import type { Dayjs } from "dayjs";
import type { CSSProperties } from "react";

const { RangePicker } = DatePicker;

/** 简化的日期时间范围选择（替代平台 CustomDateTimeRangePicker） */
export default function CustomDateTimeRangePicker(props: {
  value?: [Dayjs, Dayjs] | null;
  onChange?: (v: [Dayjs, Dayjs] | null) => void;
  style?: CSSProperties;
  className?: string;
  "aria-label"?: string;
}) {
  const { value, onChange, style, className, "aria-label": ariaLabel } = props;
  return (
    <RangePicker
      showTime
      className={className}
      style={{ width: "100%", ...style }}
      value={value}
      aria-label={ariaLabel}
      onChange={(dates) => {
        if (!dates?.[0] || !dates[1]) {
          onChange?.(null);
          return;
        }
        onChange?.([dates[0], dates[1]]);
      }}
    />
  );
}
