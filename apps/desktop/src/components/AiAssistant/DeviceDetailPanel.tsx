/**
 * 设备详情结构化展示（get_device_detail Workspace）
 * 布局：顶部摘要 + 分组字段，启用态映射可读标签（平台 deviceStatus）。
 */
import type { ReactNode } from "react";
import { Typography } from "antd";
import { useIntl } from "@umijs/max";
import type { DeviceDetailRecord, DeviceDetailWorkspace } from "./types";
import styles from "./index.module.less";

const { Text, Title } = Typography;

/** 设备名称中常见的 IP 括号形态，如「B口门禁[172.168.1.43]」 */
const IP_IN_NAME_RE = /\[((?:\d{1,3}\.){3}\d{1,3})\]/;

function displayValue(value: unknown): string {
  if (value == null || value === "") return "-";
  return String(value);
}

function hasValue(value: unknown): boolean {
  return value != null && value !== "";
}

/** 平台 deviceStatus / enableStatus：0 停用 / 1 启用 */
function resolveEnableLabel(
  device: DeviceDetailRecord,
  enabledText: string,
  disabledText: string,
): string | undefined {
  if (device.enableStatusLabel) return device.enableStatusLabel;
  if (device.deviceStatusLabel) return device.deviceStatusLabel;
  const code = device.deviceStatus ?? device.enableStatus;
  if (code === 1 || code === "1") return enabledText;
  if (code === 0 || code === "0") return disabledText;
  return undefined;
}

function resolveIpAddress(device: DeviceDetailRecord): string | undefined {
  if (hasValue(device.ipAddress)) return String(device.ipAddress);
  const fromName = device.deviceName?.match(IP_IN_NAME_RE)?.[1];
  return fromName || undefined;
}

type StatusTone = "online" | "offline" | "abnormal" | "enabled" | "disabled" | "neutral";

const STATUS_TONE_CLASS: Record<StatusTone, string> = {
  online: styles.deviceDetailStatus_online,
  offline: styles.deviceDetailStatus_offline,
  abnormal: styles.deviceDetailStatus_abnormal,
  enabled: styles.deviceDetailStatus_enabled,
  disabled: styles.deviceDetailStatus_disabled,
  neutral: styles.deviceDetailStatus_neutral,
};

function onlineTone(label?: string): StatusTone {
  if (!label) return "neutral";
  if (label.includes("在线") || /online/i.test(label)) return "online";
  if (label.includes("离线") || /offline/i.test(label)) return "offline";
  if (label.includes("异常") || /abnormal/i.test(label)) return "abnormal";
  return "neutral";
}

function enableTone(label?: string): StatusTone {
  if (!label) return "neutral";
  if (label.includes("启用") || /enabled/i.test(label)) return "enabled";
  if (label.includes("停用") || /disabled/i.test(label)) return "disabled";
  return "neutral";
}

function StatusTag({ label, tone }: { label: string; tone: StatusTone }) {
  return (
    <span className={`${styles.deviceDetailStatusTag} ${STATUS_TONE_CLASS[tone]}`}>
      <i className={styles.deviceDetailStatusDot} aria-hidden />
      {label}
    </span>
  );
}

type DetailField = {
  key: string;
  label: string;
  value: ReactNode;
};

type DetailSection = {
  key: string;
  title: string;
  fields: DetailField[];
};

function FieldRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className={styles.deviceDetailField}>
      <span className={styles.deviceDetailFieldLabel}>{label}</span>
      <span className={styles.deviceDetailFieldValue}>{value}</span>
    </div>
  );
}

export function DeviceDetailPanel({ data }: { data: DeviceDetailWorkspace }) {
  const intl = useIntl();

  if (!data.ok) {
    return (
      <Text type="danger" className={styles.workspaceError}>
        {data.summary || intl.formatMessage({ id: "aiAssistant.workspace.deviceQueryFailed" })}
      </Text>
    );
  }

  const device = data.device;
  const enabledText = intl.formatMessage({
    id: "aiAssistant.workspace.deviceEnable.enabled",
  });
  const disabledText = intl.formatMessage({
    id: "aiAssistant.workspace.deviceEnable.disabled",
  });
  const enableLabel = resolveEnableLabel(device, enabledText, disabledText);
  const onlineLabel = device.onlineStatusLabel;
  const ipAddress = resolveIpAddress(device);

  // 在线/启用状态已在顶部摘要展示，基础信息区不再重复
  const basicFields: DetailField[] = [
    {
      key: "ipAddress",
      label: intl.formatMessage({ id: "aiAssistant.workspace.deviceCol.ip" }),
      value: displayValue(ipAddress),
    },
    {
      key: "port",
      label: intl.formatMessage({ id: "aiAssistant.workspace.deviceCol.port" }),
      value: displayValue(device.port),
    },
  ];

  const ownershipFields: DetailField[] = [
    {
      key: "regionName",
      label: intl.formatMessage({
        id: "aiAssistant.workspace.deviceCol.region",
      }),
      value: displayValue(device.regionName),
    },
    {
      key: "subSystemName",
      label: intl.formatMessage({
        id: "aiAssistant.workspace.deviceCol.subsystem",
      }),
      value: displayValue(device.subSystemName),
    },
    {
      key: "deviceGroupName",
      label: intl.formatMessage({
        id: "aiAssistant.workspace.deviceCol.group",
      }),
      value: displayValue(device.deviceGroupName),
    },
    {
      key: "location",
      label: intl.formatMessage({
        id: "aiAssistant.workspace.deviceCol.location",
      }),
      value: displayValue(device.location),
    },
  ];

  const hardwareFields: DetailField[] = [
    {
      key: "manufacturer",
      label: intl.formatMessage({
        id: "aiAssistant.workspace.deviceCol.manufacturer",
      }),
      value: displayValue(device.manufacturer),
    },
    {
      key: "model",
      label: intl.formatMessage({
        id: "aiAssistant.workspace.deviceCol.model",
      }),
      value: displayValue(device.model),
    },
  ];

  const opsFields: DetailField[] = [
    {
      key: "collectServerName",
      label: intl.formatMessage({
        id: "aiAssistant.workspace.deviceCol.collectServer",
      }),
      value: displayValue(device.collectServerName),
    },
    {
      key: "commDeviceName",
      label: intl.formatMessage({
        id: "aiAssistant.workspace.deviceCol.commDevice",
      }),
      value: displayValue(device.commDeviceName),
    },
    {
      key: "firstUseTime",
      label: intl.formatMessage({
        id: "aiAssistant.workspace.deviceCol.firstUseTime",
      }),
      value: displayValue(device.firstUseTime),
    },
  ];

  const sections: DetailSection[] = [
    {
      key: "basic",
      title: intl.formatMessage({
        id: "aiAssistant.workspace.deviceSection.basic",
      }),
      fields: basicFields,
    },
    {
      key: "ownership",
      title: intl.formatMessage({
        id: "aiAssistant.workspace.deviceSection.ownership",
      }),
      fields: ownershipFields,
    },
    {
      key: "hardware",
      title: intl.formatMessage({
        id: "aiAssistant.workspace.deviceSection.network",
      }),
      fields: hardwareFields,
    },
    {
      key: "ops",
      title: intl.formatMessage({
        id: "aiAssistant.workspace.deviceSection.ops",
      }),
      fields: opsFields,
    },
  ];

  return (
    <div className={styles.deviceDetailPanel}>
      <div className={styles.deviceDetailHero}>
        <div className={styles.deviceDetailHeroMain}>
          <Title level={5} className={styles.deviceDetailName}>
            {displayValue(device.deviceName)}
          </Title>
          <Text
            type="secondary"
            className={styles.deviceDetailCode}
            copyable={hasValue(device.deviceCode) ? { text: String(device.deviceCode) } : false}
          >
            {intl.formatMessage({ id: "aiAssistant.workspace.deviceCol.code" })}：
            {displayValue(device.deviceCode)}
          </Text>
        </div>
        <div className={styles.deviceDetailTags}>
          {onlineLabel ? <StatusTag label={onlineLabel} tone={onlineTone(onlineLabel)} /> : null}
          {enableLabel ? <StatusTag label={enableLabel} tone={enableTone(enableLabel)} /> : null}
        </div>
      </div>

      <div className={styles.deviceDetailSections}>
        {sections.map((section) => (
          <section key={section.key} className={styles.deviceDetailSection}>
            <div className={styles.deviceDetailSectionTitle}>{section.title}</div>
            <div className={styles.deviceDetailGrid}>
              {section.fields.map((field) => (
                <FieldRow key={field.key} label={field.label} value={field.value} />
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
