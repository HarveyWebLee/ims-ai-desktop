/**
 * HITL 设备变量下拉：依赖同行 device_picker 或字段固定 deviceCode
 * 始终展示该设备下全部变量（不按 isWrite 过滤）
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { Form, Select, Typography } from "antd";
import { useIntl } from "react-intl";
import { getVarListByCode } from "@/services/SystemController";
import styles from "./index.module.less";

const { Text } = Typography;

interface VariableOption {
  label: string;
  value: string;
}

export interface HitlVariablePickerProps {
  value?: string;
  onChange?: (value: string | undefined) => void;
  /** 固定设备编码（无同行 device_picker 时） */
  deviceCode?: string;
  /** 依赖的设备编码字段名，默认 device_code */
  dependsOn?: string;
}

function extractRecords(data: unknown): Record<string, unknown>[] {
  if (Array.isArray(data)) {
    return data as Record<string, unknown>[];
  }
  if (data && typeof data === "object") {
    const obj = data as Record<string, unknown>;
    for (const key of ["records", "list", "rows", "data", "items"]) {
      if (Array.isArray(obj[key])) {
        return obj[key] as Record<string, unknown>[];
      }
    }
  }
  return [];
}

function toOptions(records: Record<string, unknown>[]): VariableOption[] {
  return records
    .map((item) => {
      const varName = String(item.varName ?? item.var_name ?? item.variableName ?? "").trim();
      const showName = String(
        item.showName ?? item.show_name ?? item.variableShowName ?? "",
      ).trim();
      if (!varName && !showName) return null;
      const value = varName || showName;
      const label = showName
        ? varName && showName !== varName
          ? `${showName} (${varName})`
          : showName
        : varName;
      return { label, value };
    })
    .filter((item): item is VariableOption => item != null);
}

export default function HitlVariablePicker({
  value,
  onChange,
  deviceCode: fixedDeviceCode,
  dependsOn = "device_code",
}: HitlVariablePickerProps) {
  const intl = useIntl();
  const form = Form.useFormInstance();
  const watchedDeviceCode = Form.useWatch(dependsOn, form);
  const deviceCode = String(fixedDeviceCode || watchedDeviceCode || "").trim();

  const [loading, setLoading] = useState(false);
  const [options, setOptions] = useState<VariableOption[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const prevDeviceRef = useRef<string>("");

  useEffect(() => {
    const prev = prevDeviceRef.current;
    if (prev && prev !== deviceCode) {
      onChange?.(undefined);
      if (form.getFieldValue("variable_value") != null) {
        form.setFieldValue("variable_value", undefined);
      }
    }
    prevDeviceRef.current = deviceCode;
    // 仅随设备编码切换清理；避免 Form.onChange 引用变化误清
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [deviceCode]);

  useEffect(() => {
    let cancelled = false;
    if (!deviceCode) {
      setOptions([]);
      setLoadError(null);
      setLoading(false);
      return () => {
        cancelled = true;
      };
    }

    setLoading(true);
    setLoadError(null);
    void (async () => {
      try {
        const res = await getVarListByCode({ deviceCode });
        if (cancelled) return;
        if (Number(res?.code) === 0) {
          const next = toOptions(extractRecords(res.data));
          setOptions(next);
          if (next.length === 0) {
            setLoadError(intl.formatMessage({ id: "aiAssistant.hitl.variable.empty" }));
          }
        } else {
          setOptions([]);
          setLoadError(
            String(res?.message || "").trim() ||
              intl.formatMessage({
                id: "aiAssistant.hitl.variable.loadFailed",
              }),
          );
        }
      } catch {
        if (!cancelled) {
          setOptions([]);
          setLoadError(intl.formatMessage({ id: "aiAssistant.hitl.variable.loadFailed" }));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [deviceCode, intl]);

  const placeholder = useMemo(() => {
    if (!deviceCode) {
      return intl.formatMessage({
        id: "aiAssistant.hitl.variable.needDevice",
      });
    }
    return intl.formatMessage({
      id: "aiAssistant.hitl.variable.placeholder",
    });
  }, [deviceCode, intl]);

  return (
    <div className={styles.hitlVariablePicker}>
      {!deviceCode ? (
        <Text type="secondary" className={styles.hitlVariablePickerHint}>
          {intl.formatMessage({ id: "aiAssistant.hitl.variable.needDevice" })}
        </Text>
      ) : null}
      <Select
        value={value || undefined}
        onChange={(next) => onChange?.(next || undefined)}
        options={options}
        loading={loading}
        disabled={!deviceCode}
        showSearch
        allowClear
        optionFilterProp="label"
        size="middle"
        style={{ width: "100%" }}
        placeholder={placeholder}
        notFoundContent={
          loading
            ? null
            : loadError || intl.formatMessage({ id: "aiAssistant.hitl.variable.empty" })
        }
      />
    </div>
  );
}
