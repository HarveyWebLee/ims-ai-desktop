/**
 * 配置与管理页：知识与术语 / 可观测 / 审计日志 / 语音偏好 / 声纹库
 */
import { ArrowLeftOutlined } from "@ant-design/icons";
import { Button, Layout, Tabs, Typography, theme } from "antd";
import { useIntl } from "react-intl";
import KnowledgeTermsPanel from "@/components/AiAssistant/KnowledgeTermsPanel";
import AuditLogPanel from "@/components/AiAssistant/AuditLogDrawer";
import ObservabilityDashboard from "@/components/AiAssistant/ObservabilityDashboard";
import VoiceprintManagerPanel from "@/components/AiAssistant/VoiceprintManagerModal";
import VoicePrefsPanel from "@/components/AiAssistant/VoicePrefsPanel";
import styles from "@/components/AiAssistant/index.module.less";

const { Header, Content } = Layout;
const { Title, Text } = Typography;

export default function SettingsPage({ onBack }: { onBack: () => void }) {
  const intl = useIntl();
  const { token } = theme.useToken();

  return (
    <Layout className={styles.settingsRoot}>
      <Header className={styles.settingsHeader}>
        <div className={styles.settingsHeaderLeft}>
          <Button
            type="text"
            icon={<ArrowLeftOutlined />}
            onClick={onBack}
            className={styles.desktopHeaderIconBtn}
            aria-label={intl.formatMessage({ id: "aiAssistant.settings.back" })}
          />
          <div className={styles.desktopTitleText}>
            <Title level={4} className={styles.settingsTitle}>
              {intl.formatMessage({ id: "aiAssistant.settings.title" })}
            </Title>
            <Text type="secondary" className={styles.desktopTitleSub}>
              {intl.formatMessage({ id: "aiAssistant.settings.subtitle" })}
            </Text>
          </div>
        </div>
      </Header>
      <Content className={styles.settingsContent} style={{ background: token.colorBgLayout }}>
        <div className={styles.settingsInnerWide}>
          <Tabs
            defaultActiveKey="knowledgeTerms"
            size="large"
            items={[
              {
                key: "knowledgeTerms",
                label: intl.formatMessage({ id: "aiAssistant.settings.tabKnowledgeTerms" }),
                children: <KnowledgeTermsPanel />,
              },
              {
                key: "observability",
                label: intl.formatMessage({ id: "aiAssistant.settings.tabObservability" }),
                children: <ObservabilityDashboard />,
              },
              {
                key: "audit",
                label: intl.formatMessage({ id: "aiAssistant.settings.tabAudit" }),
                children: <AuditLogPanel />,
              },
              {
                key: "voice",
                label: intl.formatMessage({ id: "aiAssistant.settings.tabVoice" }),
                children: <VoicePrefsPanel />,
              },
              {
                key: "voiceprint",
                label: intl.formatMessage({ id: "aiAssistant.settings.tabVoiceprint" }),
                children: <VoiceprintManagerPanel />,
              },
            ]}
          />
        </div>
      </Content>
    </Layout>
  );
}
