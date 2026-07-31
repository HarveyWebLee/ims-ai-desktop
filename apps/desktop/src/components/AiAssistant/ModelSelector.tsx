/**
 * 大模型下拉选择器（胶囊触发器 + 圆角下拉面板）
 * 数据源：@ims/agent-core/model-catalog
 */
import { Select } from "antd";
import { CaretDownOutlined } from "@ant-design/icons";
import { useIntl } from "react-intl";
import { AGENT_MODEL_CATALOG, DEFAULT_AGENT_MODEL_ID } from "@ims/agent-core/model-catalog";
import type { AgentModelId } from "@ims/shared-types";
import { useAiAssistantStore } from "./store";
import { AiMark } from "./AiAvatar";
import styles from "./index.module.less";

export default function ModelSelector({ className }: { className?: string }) {
  const intl = useIntl();
  const { selectedModelId, setSelectedModelId, isStreaming } = useAiAssistantStore();
  const currentId = selectedModelId || DEFAULT_AGENT_MODEL_ID;

  const options = AGENT_MODEL_CATALOG.filter((m) => m.enabled).map((m) => ({
    value: m.modelId,
    label: intl.formatMessage({
      id: m.labelKey,
      defaultMessage: m.modelId,
    }),
  }));

  return (
    <Select<AgentModelId>
      className={[styles.modelSelect, className].filter(Boolean).join(" ")}
      size="small"
      variant="borderless"
      value={currentId}
      options={options}
      disabled={isStreaming}
      onChange={setSelectedModelId}
      placement="topLeft"
      popupMatchSelectWidth={false}
      getPopupContainer={() => document.body}
      suffixIcon={<CaretDownOutlined className={styles.modelSelectArrow} />}
      aria-label={intl.formatMessage({ id: "aiAssistant.model.label" })}
      labelRender={({ label }) => (
        <span className={styles.modelSelectLabel}>
          <AiMark size={12} className={styles.modelSelectIcon} />
          <span className={styles.modelSelectText}>{label}</span>
        </span>
      )}
    />
  );
}
