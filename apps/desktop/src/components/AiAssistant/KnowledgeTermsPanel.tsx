/**
 * 知识与术语：文档规程 + 实体术语（设备/变量）统一入口
 */
import { Tabs } from "antd";
import { useIntl } from "react-intl";
import KnowledgeOpsPanel from "@/components/AiAssistant/KnowledgeOpsPanel";
import EntityOpsPanel from "@/components/AiAssistant/EntityOpsPanel";

export default function KnowledgeTermsPanel() {
  const intl = useIntl();

  return (
    <Tabs
      defaultActiveKey="docs"
      size="middle"
      items={[
        {
          key: "docs",
          label: intl.formatMessage({ id: "aiAssistant.settings.subTabDocs" }),
          children: <KnowledgeOpsPanel />,
        },
        {
          key: "entities",
          label: intl.formatMessage({ id: "aiAssistant.settings.subTabEntities" }),
          children: <EntityOpsPanel />,
        },
      ]}
    />
  );
}
