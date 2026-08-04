/**
 * 大模型下拉选择器（胶囊触发器 + 圆角下拉面板）
 * 数据源：@ims/agent-core/model-catalog（仅 enabled；含 Auto）
 */
import { Select } from "antd";
import { CaretDownOutlined } from "@ant-design/icons";
import { useIntl } from "react-intl";
import {
  AGENT_MODEL_CATALOG,
  AUTO_AGENT_MODEL_ID,
  DEFAULT_AGENT_MODEL_ID,
  type AgentModelSelectionId,
} from "@ims/agent-core/model-catalog";
import { useAiAssistantStore } from "./store";
import { AiMark } from "./AiAvatar";
import styles from "./index.module.less";

export default function ModelSelector({ className }: { className?: string }) {
  const intl = useIntl();
  const { selectedModelId, setSelectedModelId, isStreaming } = useAiAssistantStore();
  const currentId = selectedModelId || AUTO_AGENT_MODEL_ID;

  const options: Array<{ value: AgentModelSelectionId; label: string }> = [
    {
      value: AUTO_AGENT_MODEL_ID,
      label: intl.formatMessage({ id: "aiAssistant.model.auto" }),
    },
    ...AGENT_MODEL_CATALOG.filter((m) => m.enabled).map((m) => ({
      value: m.modelId,
      label: intl.formatMessage({
        id: m.labelKey,
        defaultMessage: m.modelId,
      }),
    })),
  ];

  // 持久化若落在已禁用项，展示回退到 Auto（实际请求也会走 resolve）
  const value = options.some((o) => o.value === currentId) ? currentId : AUTO_AGENT_MODEL_ID;

  return (
    <Select<AgentModelSelectionId>
      className={[styles.modelSelect, className].filter(Boolean).join(" ")}
      size="small"
      variant="borderless"
      value={value}
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
          <span className={styles.modelSelectText}>
            {label ||
              intl.formatMessage({
                id: `aiAssistant.model.${DEFAULT_AGENT_MODEL_ID}`,
                defaultMessage: DEFAULT_AGENT_MODEL_ID,
              })}
          </span>
        </span>
      )}
    />
  );
}
