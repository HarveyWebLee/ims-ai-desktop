/**
 * 语音相关偏好：纠错下划线标注开关
 */
import { Card, Switch, Typography } from "antd";
import { useIntl } from "react-intl";
import { useAiAssistantStore } from "./store";
import styles from "./index.module.less";

const { Text, Paragraph } = Typography;

export default function VoicePrefsPanel() {
  const intl = useIntl();
  const enabled = useAiAssistantStore((s) => s.voiceCorrectionHighlightEnabled);
  const setEnabled = useAiAssistantStore((s) => s.setVoiceCorrectionHighlightEnabled);

  return (
    <Card className={styles.voicePrefsCard} size="small">
      <div className={styles.voicePrefsRow}>
        <div className={styles.voicePrefsCopy}>
          <Text strong>
            {intl.formatMessage({ id: "aiAssistant.settings.voiceCorrectionHighlight" })}
          </Text>
          <Paragraph type="secondary" className={styles.voicePrefsDesc}>
            {intl.formatMessage({ id: "aiAssistant.settings.voiceCorrectionHighlightDesc" })}
          </Paragraph>
        </div>
        <Switch
          checked={enabled}
          onChange={setEnabled}
          checkedChildren={intl.formatMessage({ id: "aiAssistant.settings.voiceCorrectionOn" })}
          unCheckedChildren={intl.formatMessage({
            id: "aiAssistant.settings.voiceCorrectionOff",
          })}
        />
      </div>
    </Card>
  );
}
