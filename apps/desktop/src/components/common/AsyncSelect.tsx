import { useEffect, useState } from "react";
import { Select } from "antd";
import type { DefaultOptionType, SelectProps } from "antd/es/select";

type AsyncSelectProps = SelectProps & {
  /** 平台异步字典加载 */
  getListData?: (data?: unknown) => Promise<{
    code: number;
    data: unknown;
    message?: string;
  }>;
};

function toOptions(data: unknown): DefaultOptionType[] {
  const raw = Array.isArray(data)
    ? data
    : data && typeof data === "object"
      ? ((data as { list?: unknown[]; records?: unknown[] }).list ??
        (data as { records?: unknown[] }).records ??
        [])
      : [];
  if (!Array.isArray(raw)) return [];
  return raw.map((item, index) => {
    if (item == null || typeof item !== "object") {
      return { label: String(item), value: String(item ?? index) };
    }
    const row = item as Record<string, unknown>;
    const value = row.value ?? row.id ?? row.code ?? row.dicCode ?? row.key ?? index;
    const label = row.label ?? row.name ?? row.dicName ?? row.title ?? row.text ?? String(value);
    return { label: String(label), value: value as string | number };
  });
}

/** 简化 AsyncSelect：支持 getListData 拉选项 */
export default function AsyncSelect({ getListData, options, ...props }: AsyncSelectProps) {
  const [asyncOptions, setAsyncOptions] = useState<DefaultOptionType[] | undefined>(options);

  useEffect(() => {
    if (options) {
      setAsyncOptions(options);
      return;
    }
    if (!getListData) return;
    let cancelled = false;
    void getListData()
      .then((res) => {
        if (cancelled || res?.code !== 0) return;
        setAsyncOptions(toOptions(res.data));
      })
      .catch(() => {
        if (!cancelled) setAsyncOptions([]);
      });
    return () => {
      cancelled = true;
    };
  }, [getListData, options]);

  return (
    <Select allowClear showSearch optionFilterProp="label" options={asyncOptions} {...props} />
  );
}
