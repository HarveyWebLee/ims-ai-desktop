/**
 * 文本输入与发送：卡片式输入区，底部左侧模型选择、右侧语音与发送
 */
import { Button, Input, Select, Tooltip } from "antd";
import { SendOutlined } from "@ant-design/icons";
import { useIntl } from "react-intl";
import { useCallback, useEffect, useRef, useState, KeyboardEvent } from "react";
import * as AgentController from "@/services/AgentController";
import type { VoiceprintProfile } from "@/services/AgentController";
import ModelSelector from "./ModelSelector";
import VoiceInput, { type VoiceCorrectionMeta } from "./VoiceInput";
import { useAiAssistantStore } from "./store";
import styles from "./index.module.less";

const { TextArea } = Input;

function joinBaseAndVoice(base: string, voice: string): string {
  const b = base.trim();
  const v = voice.trim();
  if (!v) return b;
  if (!b) return v;
  return `${b} ${v}`;
}

function stageLabelId(stage?: string): string {
  switch (stage) {
    case "semantic":
      return "aiAssistant.voice.stage.semantic";
    case "dictionary":
      return "aiAssistant.voice.stage.dictionary";
    case "llm":
      return "aiAssistant.voice.stage.llm";
    case "cache":
      return "aiAssistant.voice.stage.cache";
    case "rule":
      return "aiAssistant.voice.stage.rule";
    default:
      return "aiAssistant.voice.stage.none";
  }
}

export default function MessageInput({
  onSend,
  disabled: inputDisabled,
}: {
  onSend: (text: string) => void;
  /** 流式中或 HITL 待确认时禁用输入 */
  disabled?: boolean;
}) {
  const intl = useIntl();
  const [text, setText] = useState("");
  const [correction, setCorrection] = useState<(VoiceCorrectionMeta & { text: string }) | null>(
    null,
  );
  const [voiceprints, setVoiceprints] = useState<VoiceprintProfile[]>([]);
  const textRef = useRef(text);
  textRef.current = text;
  /** 开始录音时锁定的已有文案；中间结果 / 终稿拼在其后 */
  const voiceBaseRef = useRef("");
  const [voiceBusy, setVoiceBusy] = useState(false);
  const { isStreaming, selectedVoiceprintId, setSelectedVoiceprintId } = useAiAssistantStore();
  const disabled = inputDisabled || isStreaming;
  const voiceprintSelectDisabled = disabled || voiceBusy;
  const canSend = Boolean(text.trim()) && !disabled;

  const refreshVoiceprints = useCallback(async () => {
    try {
      const data = await AgentController.listVoiceprints();
      const items = data.items ?? [];
      setVoiceprints(items);
      const selected = useAiAssistantStore.getState().selectedVoiceprintId;
      if (selected && !items.some((i) => i.id === selected)) {
        setSelectedVoiceprintId(null);
      }
    } catch {
      /* 列表失败不阻断输入 */
    }
  }, [setSelectedVoiceprintId]);

  useEffect(() => {
    void refreshVoiceprints();
  }, [refreshVoiceprints]);

  const handleSend = () => {
    if (!canSend) return;
    onSend(text);
    setText("");
    setCorrection(null);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleRecordingStart = () => {
    voiceBaseRef.current = textRef.current.trim();
    setCorrection(null);
  };

  const handleInterim = (interim: string) => {
    if (!interim.trim()) return;
    setText(joinBaseAndVoice(voiceBaseRef.current, interim));
  };

  const handleTranscribed = (transcribed: string, meta?: VoiceCorrectionMeta) => {
    if (!transcribed.trim()) {
      setText(voiceBaseRef.current);
      voiceBaseRef.current = "";
      setCorrection(null);
      return;
    }
    setText(joinBaseAndVoice(voiceBaseRef.current, transcribed));
    voiceBaseRef.current = "";
    if (meta && (meta.raw || meta.stage)) {
      setCorrection({ ...meta, text: transcribed });
    } else {
      setCorrection(null);
    }
  };

  const correctionHint = (() => {
    if (!correction) return null;
    const stage = intl.formatMessage({ id: stageLabelId(correction.stage) });
    const raw = (correction.raw || "").trim();
    const finalText = (correction.text || "").trim();
    if (correction.changed && raw && raw !== finalText) {
      return intl.formatMessage(
        { id: "aiAssistant.voice.correctionChanged" },
        { raw, text: finalText, stage },
      );
    }
    return intl.formatMessage({ id: "aiAssistant.voice.correctionUnchanged" }, { stage });
  })();

  const enrolledOptions = voiceprints.map((v) => ({
    value: v.id,
    label: `${v.display_name}${v.enrolled ? "" : "（未录入）"}`,
    disabled: !v.enrolled,
  }));

  return (
    <div className={styles.inputArea}>
      <div className={styles.inputAreaInner}>
        <div className={styles.inputComposer}>
          <div className={styles.inputComposerBody}>
            <TextArea
              className={styles.inputTextarea}
              value={text}
              onChange={(e) => {
                setText(e.target.value);
                if (correction) setCorrection(null);
              }}
              onKeyDown={onKeyDown}
              placeholder={intl.formatMessage({
                id: "aiAssistant.inputPlaceholder",
              })}
              autoSize={{ minRows: 3, maxRows: 8 }}
              disabled={disabled}
              variant="borderless"
            />
          </div>
          <div className={styles.inputToolbar}>
            <div className={styles.inputActionsLeft}>
              <ModelSelector />
            </div>
            <div className={styles.inputActionsRight}>
              <div className={styles.voiceControlGroup}>
                <Tooltip
                  title={
                    voiceBusy
                      ? intl.formatMessage({ id: "aiAssistant.voiceprint.lockDuringVoice" })
                      : undefined
                  }
                >
                  <Select
                    className={styles.voiceprintSelect}
                    size="small"
                    variant="borderless"
                    placeholder={intl.formatMessage({
                      id: "aiAssistant.voiceprint.selectPlaceholder",
                    })}
                    value={selectedVoiceprintId ?? undefined}
                    onChange={(id) => setSelectedVoiceprintId(id)}
                    options={enrolledOptions}
                    allowClear={!voiceBusy}
                    disabled={voiceprintSelectDisabled}
                    popupMatchSelectWidth={false}
                    style={{ minWidth: 132 }}
                  />
                </Tooltip>
                <VoiceInput
                  onRecordingStart={handleRecordingStart}
                  onInterim={handleInterim}
                  onTranscribed={handleTranscribed}
                  onBusyChange={setVoiceBusy}
                  disabled={disabled}
                />
              </div>
              <Tooltip title={intl.formatMessage({ id: "aiAssistant.send" })}>
                <Button
                  type="primary"
                  shape="circle"
                  size="large"
                  className={styles.sendBtn}
                  icon={<SendOutlined />}
                  onClick={handleSend}
                  loading={isStreaming}
                  disabled={!canSend}
                  aria-label={intl.formatMessage({ id: "aiAssistant.send" })}
                />
              </Tooltip>
            </div>
          </div>
        </div>

        {correctionHint ? (
          <p
            className={
              correction?.changed
                ? `${styles.inputHint} ${styles.voiceCorrectionHint}`
                : styles.inputHint
            }
          >
            {correctionHint}
          </p>
        ) : (
          <p className={styles.inputHint}>
            {selectedVoiceprintId
              ? intl.formatMessage({ id: "aiAssistant.inputShortcutHint" })
              : intl.formatMessage({
                  id: "aiAssistant.voiceprint.selectRequiredHint",
                })}
          </p>
        )}
      </div>
    </div>
  );
}
