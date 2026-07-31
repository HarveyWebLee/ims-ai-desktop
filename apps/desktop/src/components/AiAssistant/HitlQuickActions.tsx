/**
 * HITL 快捷操作条：固定在助手气泡顶部，避免 BPMN/计划列表过长时找不到按钮
 */
import { Alert } from "antd";
import { InteractionOutlined } from "@ant-design/icons";
import { useIntl } from "react-intl";
import type { HitlPayload } from "@ims/shared-types";
import { shouldShowHitlQuickActions } from "./utils/hitlInterruptUtils";
import styles from "./index.module.less";

export interface HitlQuickActionsProps {
  payload: HitlPayload;
}

export default function HitlQuickActions({ payload }: HitlQuickActionsProps) {
  const intl = useIntl();
  const interactive = true;
  if (!shouldShowHitlQuickActions(payload, interactive)) {
    return null;
  }

  return (
    <div className={styles.hitlQuickActions}>
      <div className={styles.hitlQuickActionsHeader}>
        <InteractionOutlined />
        <span>{intl.formatMessage({ id: "aiAssistant.card.hitl.title" })}</span>
      </div>
      {payload.message ? (
        <div className={styles.hitlQuickActionsDesc}>{payload.message}</div>
      ) : null}
      <Alert
        type="info"
        showIcon
        className={styles.hitlQuickActionsAlert}
        title={intl.formatMessage({ id: "aiAssistant.hitl.scrollToForm" })}
      />
    </div>
  );
}
