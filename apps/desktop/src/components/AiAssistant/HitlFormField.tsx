/**
 * HITL 单字段渲染：日期时间范围、下拉、异步字典等
 */
import { useMemo } from "react";
import { Input, Select } from "antd";
import type { Rule } from "antd/es/form";
import dayjs, { type Dayjs } from "dayjs";
import { useIntl } from "react-intl";
import type { HitlField } from "@ims/shared-types";
import CustomDateTimeRangePicker from "@/components/CustomDatePicker/CustomDateTimeRangePicker";
import AsyncSelect from "@/components/common/AsyncSelect";
import * as SystemController from "@/services/SystemController";
import type { HitlDateTimeRangeValue } from "./utils/hitlFormUtils";
import HitlDevicePicker from "./HitlDevicePicker";
import HitlVariablePicker from "./HitlVariablePicker";
import styles from "./index.module.less";

const PLATFORM_DATETIME = "YYYY-MM-DD HH:mm:ss";

/** 解析平台/HITL 日期时间字符串 */
function parsePlatformDatetime(raw?: string): Dayjs | null {
  if (!raw?.trim()) return null;
  const strict = dayjs(raw, PLATFORM_DATETIME, true);
  if (strict.isValid()) return strict;
  const loose = dayjs(raw);
  return loose.isValid() ? loose : null;
}

interface HitlDateTimeRangeInputProps {
  value?: HitlDateTimeRangeValue;
  onChange?: (value: HitlDateTimeRangeValue) => void;
  placeholder?: string;
}

/** 告警查询 HITL：开始/结束日期时间（精确到秒） */
function HitlDateTimeRangeInput({ value, onChange, placeholder }: HitlDateTimeRangeInputProps) {
  const pickerValue = useMemo((): [Dayjs, Dayjs] | null => {
    const start = parsePlatformDatetime(value?.start_time);
    const end = parsePlatformDatetime(value?.end_time);
    if (start && end) {
      return [start, end];
    }
    return null;
  }, [value?.end_time, value?.start_time]);

  return (
    <CustomDateTimeRangePicker
      className={styles.hitlDateTimeRange}
      value={pickerValue}
      onChange={(range) => {
        if (!range?.[0] || !range[1]) {
          onChange?.({});
          return;
        }
        onChange?.({
          start_time: range[0].format(PLATFORM_DATETIME),
          end_time: range[1].format(PLATFORM_DATETIME),
        });
      }}
      {...(placeholder ? { "aria-label": placeholder } : {})}
    />
  );
}

export interface HitlFormFieldProps {
  field: HitlField;
  /** Form.Item 注入的受控值 */
  value?: unknown;
  /** Form.Item 注入的变更回调 */
  onChange?: (value: unknown) => void;
}

export default function HitlFormField({ field, value, onChange }: HitlFormFieldProps) {
  const intl = useIntl();
  const selectPlaceholder = intl.formatMessage({
    id: "aiAssistant.hitl.selectPlaceholder",
  });

  if (field.type === "datetime_range") {
    return (
      <HitlDateTimeRangeInput
        value={value as HitlDateTimeRangeValue | undefined}
        onChange={onChange as HitlDateTimeRangeInputProps["onChange"]}
        placeholder={field.description}
      />
    );
  }

  if (field.type === "device_picker") {
    return (
      <HitlDevicePicker
        value={typeof value === "string" ? value : undefined}
        onChange={(code) => onChange?.(code)}
        description={field.description}
      />
    );
  }

  if (field.type === "variable_picker") {
    return (
      <HitlVariablePicker
        value={typeof value === "string" ? value : undefined}
        onChange={(varName) => onChange?.(varName)}
        deviceCode={field.deviceCode}
        dependsOn={field.dependsOn}
      />
    );
  }

  if (field.type === "async_select") {
    const getListData =
      field.asyncSource === "alarm_category"
        ? SystemController.getAlarmCategoryList
        : SystemController.getAlarmRankList;

    return (
      <AsyncSelect
        value={value}
        onChange={onChange}
        getListData={getListData}
        allowClear
        mode={field.mode === "multiple" ? "multiple" : undefined}
        size="middle"
        placeholder={selectPlaceholder}
        style={{ width: "100%" }}
      />
    );
  }

  if (field.type === "select") {
    return (
      <Select
        value={value}
        onChange={onChange}
        options={field.options}
        showSearch
        allowClear
        optionFilterProp="label"
        mode={field.mode === "multiple" ? "multiple" : undefined}
        size="middle"
        placeholder={selectPlaceholder}
      />
    );
  }

  return (
    <Input
      value={value as string | undefined}
      onChange={(e) => onChange?.(e.target.value)}
      placeholder={field.description}
      size="middle"
    />
  );
}

/** 按字段类型生成 Form.Item 校验规则 */
export function buildHitlFieldRules(field: HitlField, intl: ReturnType<typeof useIntl>): Rule[] {
  if (!field.required) return [];

  if (field.type === "datetime_range") {
    return [
      {
        validator: async (_, value: HitlDateTimeRangeValue | undefined) => {
          if (!value?.start_time || !value?.end_time) {
            throw new Error(intl.formatMessage({ id: "pleaseSelect" }, { name: field.label }));
          }
        },
      },
    ];
  }

  return [
    {
      required: true,
      message: intl.formatMessage(
        field.type === "select" ||
          field.type === "async_select" ||
          field.type === "device_picker" ||
          field.type === "variable_picker"
          ? { id: "pleaseSelect" }
          : { id: "pleaseInput" },
        { name: field.label },
      ),
    },
  ];
}
