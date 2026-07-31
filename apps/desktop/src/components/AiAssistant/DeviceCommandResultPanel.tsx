/**
 * 设备指令下发结果卡（send_device_cmd Workspace）
 * 由 tool_end 结构化驱动，与具体大模型无关。
 */
import { CheckCircleFilled, CloseCircleFilled, StopOutlined } from "@ant-design/icons";
import { Typography } from "antd";
import { useIntl } from "@umijs/max";
import type { DeviceCommandWorkspace } from "./types";
import styles from "./index.module.less";

const { Text } = Typography;

function displayValue(value: string | undefined): string {
  if (value == null || value === "") return "-";
  return value;
}

type FieldItem = { key: string; label: string; value: string };

export default function DeviceCommandResultPanel({ data }: { data: DeviceCommandWorkspace }) {
  const intl = useIntl();

  const toneClass = data.userCancelled
    ? styles.deviceCmdTone_cancelled
    : data.ok
      ? styles.deviceCmdTone_ok
      : styles.deviceCmdTone_error;

  const StatusIcon = data.userCancelled
    ? StopOutlined
    : data.ok
      ? CheckCircleFilled
      : CloseCircleFilled;

  const statusLabel = data.userCancelled
    ? intl.formatMessage({ id: "aiAssistant.workspace.deviceCmdCancelled" })
    : data.ok
      ? intl.formatMessage({ id: "aiAssistant.workspace.deviceCmdSuccess" })
      : intl.formatMessage({ id: "aiAssistant.workspace.deviceCmdFailed" });

  const fields: FieldItem[] = [
    {
      key: "device",
      label: intl.formatMessage({
        id: "aiAssistant.workspace.deviceCmdCol.device",
      }),
      value: data.deviceName
        ? data.deviceCode
          ? `${data.deviceName}（${data.deviceCode}）`
          : data.deviceName
        : displayValue(data.deviceCode),
    },
    {
      key: "variable",
      label: intl.formatMessage({
        id: "aiAssistant.workspace.deviceCmdCol.variable",
      }),
      value: displayValue(data.variableName),
    },
    {
      key: "value",
      label: intl.formatMessage({
        id: "aiAssistant.workspace.deviceCmdCol.value",
      }),
      value: displayValue(data.variableValue),
    },
    {
      key: "taskNo",
      label: intl.formatMessage({
        id: "aiAssistant.workspace.deviceCmdCol.taskNo",
      }),
      value: displayValue(data.taskNo),
    },
  ].filter((f) => f.value !== "-");

  return (
    <div className={`${styles.deviceCmdPanel} ${toneClass}`}>
      <div className={styles.deviceCmdHero}>
        <StatusIcon className={styles.deviceCmdStatusIcon} aria-hidden />
        <div className={styles.deviceCmdHeroMain}>
          <div className={styles.deviceCmdStatus}>{statusLabel}</div>
          {data.summary ? <Text className={styles.deviceCmdSummary}>{data.summary}</Text> : null}
        </div>
      </div>

      {fields.length > 0 ? (
        <div className={styles.deviceCmdGrid}>
          {fields.map((field) => (
            <div key={field.key} className={styles.deviceCmdField}>
              <span className={styles.deviceCmdFieldLabel}>{field.label}</span>
              <span className={styles.deviceCmdFieldValue}>{field.value}</span>
            </div>
          ))}
        </div>
      ) : null}

      {data.autoRetry ? (
        <Text type="secondary" className={styles.deviceCmdRetry}>
          {intl.formatMessage(
            { id: "aiAssistant.workspace.deviceCmdAutoRetry" },
            { from: data.autoRetry.from, to: data.autoRetry.to },
          )}
        </Text>
      ) : null}
    </div>
  );
}
