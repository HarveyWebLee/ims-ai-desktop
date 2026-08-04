/**
 * 导出/下载结果卡（download_file Workspace）
 * 展示摘要与文件名；实际下载仍由 client_action 执行。
 */
import { CheckCircleFilled, CloseCircleFilled, StopOutlined } from "@ant-design/icons";
import { Typography } from "antd";
import { useIntl } from "react-intl";
import type { ExportDownloadWorkspace } from "./types";
import styles from "./index.module.less";

const { Text } = Typography;

function displayValue(value: string | number | undefined): string {
  if (value == null || value === "") return "-";
  return String(value);
}

type FieldItem = { key: string; label: string; value: string };

export default function ExportResultPanel({ data }: { data: ExportDownloadWorkspace }) {
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
    ? intl.formatMessage({ id: "aiAssistant.workspace.exportCancelled" })
    : data.ok
      ? intl.formatMessage({ id: "aiAssistant.workspace.exportSuccess" })
      : intl.formatMessage({ id: "aiAssistant.workspace.exportFailed" });

  const fields: FieldItem[] = [
    {
      key: "resource",
      label: intl.formatMessage({ id: "aiAssistant.workspace.exportCol.resource" }),
      value: displayValue(data.resource),
    },
    {
      key: "total",
      label: intl.formatMessage({ id: "aiAssistant.workspace.exportCol.total" }),
      value: data.total != null ? String(data.total) : "-",
    },
    {
      key: "batchCount",
      label: intl.formatMessage({ id: "aiAssistant.workspace.exportCol.batchCount" }),
      value: data.batchCount != null ? String(data.batchCount) : "-",
    },
  ].filter((f) => f.value !== "-");

  const fileNames =
    data.files
      ?.map((f) => f.filename || f.url)
      .filter((v): v is string => Boolean(v && String(v).trim())) ?? [];

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

      {fileNames.length > 0 ? (
        <div className={styles.exportFileList}>
          <Text type="secondary" className={styles.exportFileLabel}>
            {intl.formatMessage({ id: "aiAssistant.workspace.exportCol.files" })}
          </Text>
          <ul className={styles.exportFileItems}>
            {fileNames.map((name) => (
              <li key={name}>{name}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
