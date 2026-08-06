/**
 * 文本输入与发送：卡片式输入区，底部左侧模型选择、右侧语音与发送。
 * 语音按段纠错；ASR 与纠错均实时写回输入框；可选下划线标注纠错段。
 */
import { Button, Input, Segmented, Select, Switch, Tooltip } from "antd";
import { PauseOutlined, SendOutlined } from "@ant-design/icons";
import { useIntl } from "react-intl";
import { useCallback, useEffect, useRef, useState, KeyboardEvent } from "react";
import type { AgentRunMode } from "@ims/shared-types";
import * as AgentController from "@/services/AgentController";
import type { VoiceprintProfile } from "@/services/AgentController";
import ModelSelector from "./ModelSelector";
import VoiceInput, { type VoiceCorrectionMeta, type VoiceSegment } from "./VoiceInput";
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

export default function MessageInput({
  onSend,
  onAbort,
  disabled: inputDisabled,
}: {
  onSend: (text: string) => void;
  /** 流式中中止当前回复 */
  onAbort?: () => void;
  /** HITL 待确认或拉取历史时禁用输入；流式中仍可预输入/语音，仅禁止发送 */
  disabled?: boolean;
}) {
  const intl = useIntl();
  const [text, setText] = useState("");
  const [voiceSegments, setVoiceSegments] = useState<VoiceSegment[]>([]);
  const [voicePreview, setVoicePreview] = useState("");
  /** 本轮录音开始时锁定的键盘文案（标注层拼接用，手动编辑后清除） */
  const [lockedVoiceBase, setLockedVoiceBase] = useState("");
  /** view：可悬停下划线；edit：普通 TextArea（点击标注层后进入） */
  const [annotationMode, setAnnotationMode] = useState<"view" | "edit">("edit");
  const [voiceprints, setVoiceprints] = useState<VoiceprintProfile[]>([]);
  const textRef = useRef(text);
  textRef.current = text;
  /** 开始录音时锁定的已有文案；中间结果 / 终稿拼在其后 */
  const voiceBaseRef = useRef("");
  const [voiceBusy, setVoiceBusy] = useState(false);
  const {
    isStreaming,
    selectedVoiceprintId,
    setSelectedVoiceprintId,
    voiceprintEnabled,
    setVoiceprintEnabled,
    voiceCorrectionHighlightEnabled,
    runMode,
    setRunMode,
    planFirst,
    setPlanFirst,
    pendingInterrupt,
  } = useAiAssistantStore();
  /** HITL / 拉历史时锁定编辑；流式中允许预录入 */
  const composeDisabled = Boolean(inputDisabled);
  /** 流式未结束或输入锁定时禁止发送 */
  const sendBlocked = composeDisabled || isStreaming;
  const runModeDisabled = composeDisabled || isStreaming || Boolean(pendingInterrupt);
  const voiceprintSelectDisabled = composeDisabled || voiceBusy;
  const canSend = Boolean(text.trim()) && !sendBlocked;
  const canAbort = isStreaming && Boolean(onAbort);

  const hasCorrectionMarks =
    voiceCorrectionHighlightEnabled && voiceSegments.some((s) => s.changed && s.text.trim());
  // 开标注时：录音/转写全程用标注层实时回显；关标注则只用 TextArea
  const showAnnotationOverlay =
    voiceCorrectionHighlightEnabled &&
    annotationMode === "view" &&
    (voiceBusy || voiceSegments.length > 0 || Boolean(voicePreview.trim()));

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
    let cancelled = false;
    void (async () => {
      try {
        const cfg = await AgentController.getVoiceprintConfig();
        if (cancelled) return;
        setVoiceprintEnabled(Boolean(cfg.enabled));
        if (cfg.enabled) {
          await refreshVoiceprints();
        }
      } catch {
        if (!cancelled) setVoiceprintEnabled(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [refreshVoiceprints, setVoiceprintEnabled]);

  const clearVoiceAnnotations = useCallback(() => {
    setVoiceSegments([]);
    setVoicePreview("");
    setLockedVoiceBase("");
    setAnnotationMode("edit");
  }, []);

  const handleSend = () => {
    if (!canSend) return;
    onSend(text);
    setText("");
    clearVoiceAnnotations();
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleRecordingStart = useCallback(() => {
    const base = textRef.current.trim();
    voiceBaseRef.current = base;
    setLockedVoiceBase(base);
    setVoiceSegments([]);
    setVoicePreview("");
    setAnnotationMode(voiceCorrectionHighlightEnabled ? "view" : "edit");
  }, [voiceCorrectionHighlightEnabled]);

  const handleInterim = useCallback(
    (payload: { text: string; preview: string; segments: VoiceSegment[] }) => {
      const draft = payload.text.trim();
      setText(joinBaseAndVoice(voiceBaseRef.current, draft));
      setVoiceSegments(payload.segments);
      setVoicePreview(payload.preview || "");
      if (voiceCorrectionHighlightEnabled) {
        setAnnotationMode("view");
      }
    },
    [voiceCorrectionHighlightEnabled],
  );

  const handleTranscribed = useCallback(
    (transcribed: string, meta?: VoiceCorrectionMeta) => {
      if (!transcribed.trim()) {
        setText(voiceBaseRef.current);
        voiceBaseRef.current = "";
        clearVoiceAnnotations();
        return;
      }
      setText(joinBaseAndVoice(voiceBaseRef.current, transcribed));
      voiceBaseRef.current = "";
      const segs = meta?.segments ?? [];
      setVoiceSegments(segs);
      setVoicePreview("");
      setAnnotationMode(voiceCorrectionHighlightEnabled && segs.length > 0 ? "view" : "edit");
    },
    [clearVoiceAnnotations, voiceCorrectionHighlightEnabled],
  );

  const enrolledOptions = voiceprints.map((v) => ({
    value: v.id,
    label: `${v.display_name}${v.enrolled ? "" : "（未录入）"}`,
    disabled: !v.enrolled,
  }));

  const basePrefix = lockedVoiceBase.trim();

  return (
    <div className={styles.inputArea}>
      <div className={styles.inputAreaInner}>
        <div className={styles.inputComposer}>
          <div className={styles.inputComposerBody}>
            <div className={styles.annotatedInputWrap}>
              {showAnnotationOverlay ? (
                <div
                  className={styles.annotateBackdrop}
                  onClick={() => {
                    if (!voiceBusy) setAnnotationMode("edit");
                  }}
                  role="presentation"
                >
                  {basePrefix ? <span>{basePrefix} </span> : null}
                  {voiceSegments.map((seg) =>
                    seg.changed && seg.text ? (
                      <Tooltip
                        key={seg.seq}
                        title={intl.formatMessage(
                          { id: "aiAssistant.voice.correctionHoverRaw" },
                          { raw: seg.raw || seg.text },
                        )}
                      >
                        <span className={styles.correctedMark} onClick={(e) => e.stopPropagation()}>
                          {seg.text}
                        </span>
                      </Tooltip>
                    ) : (
                      <span key={seg.seq}>{seg.text}</span>
                    ),
                  )}
                  {voicePreview ? (
                    <span className={styles.voicePreviewMark}>{voicePreview}</span>
                  ) : null}
                </div>
              ) : null}
              <TextArea
                className={
                  showAnnotationOverlay
                    ? `${styles.inputTextarea} ${styles.inputTextareaOverlay}`
                    : styles.inputTextarea
                }
                value={text}
                onChange={(e) => {
                  setText(e.target.value);
                  clearVoiceAnnotations();
                }}
                onKeyDown={onKeyDown}
                onFocus={() => {
                  if (showAnnotationOverlay && !voiceBusy) setAnnotationMode("edit");
                }}
                placeholder={intl.formatMessage({
                  id: isStreaming
                    ? "aiAssistant.inputPlaceholderWhileStreaming"
                    : "aiAssistant.inputPlaceholder",
                })}
                autoSize={{ minRows: 3, maxRows: 8 }}
                disabled={composeDisabled}
                variant="borderless"
              />
            </div>
          </div>
          <div className={styles.inputToolbar}>
            <div className={styles.inputActionsLeft}>
              <ModelSelector />
              <Tooltip title={intl.formatMessage({ id: "aiAssistant.runMode.tip" })}>
                <Segmented<AgentRunMode>
                  size="small"
                  className={styles.runModeSegmented}
                  disabled={runModeDisabled}
                  value={runMode}
                  onChange={(value) => setRunMode(value)}
                  options={[
                    {
                      label: intl.formatMessage({ id: "aiAssistant.runMode.readonly" }),
                      value: "readonly",
                    },
                    {
                      label: intl.formatMessage({ id: "aiAssistant.runMode.confirm" }),
                      value: "confirm",
                    },
                    {
                      label: intl.formatMessage({ id: "aiAssistant.runMode.autonomous" }),
                      value: "autonomous",
                    },
                  ]}
                />
              </Tooltip>
              <Tooltip title={intl.formatMessage({ id: "aiAssistant.planFirst.tip" })}>
                <span className={styles.planFirstSwitch}>
                  <Switch
                    size="small"
                    checked={planFirst}
                    disabled={runModeDisabled}
                    onChange={setPlanFirst}
                  />
                  <span className={styles.planFirstLabel}>
                    {intl.formatMessage({ id: "aiAssistant.planFirst.label" })}
                  </span>
                </span>
              </Tooltip>
            </div>
            <div className={styles.inputActionsRight}>
              <div className={styles.voiceControlGroup}>
                {voiceprintEnabled ? (
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
                ) : null}
                <VoiceInput
                  onRecordingStart={handleRecordingStart}
                  onInterim={handleInterim}
                  onTranscribed={handleTranscribed}
                  onBusyChange={setVoiceBusy}
                  disabled={composeDisabled}
                />
              </div>
              {canAbort ? (
                <Tooltip title={intl.formatMessage({ id: "aiAssistant.abort" })}>
                  <Button
                    type="primary"
                    shape="circle"
                    size="large"
                    className={`${styles.sendBtn} ${styles.abortBtn}`}
                    icon={<PauseOutlined className={styles.abortIcon} />}
                    onClick={() => onAbort?.()}
                    aria-label={intl.formatMessage({ id: "aiAssistant.abort" })}
                  />
                </Tooltip>
              ) : (
                <Tooltip
                  title={intl.formatMessage({
                    id: sendBlocked ? "aiAssistant.sendBlockedWhileBusy" : "aiAssistant.send",
                  })}
                >
                  <Button
                    type="primary"
                    shape="circle"
                    size="large"
                    className={styles.sendBtn}
                    icon={<SendOutlined />}
                    onClick={handleSend}
                    disabled={!canSend}
                    aria-label={intl.formatMessage({ id: "aiAssistant.send" })}
                  />
                </Tooltip>
              )}
            </div>
          </div>
        </div>

        <p className={styles.inputHint}>
          {hasCorrectionMarks
            ? intl.formatMessage({ id: "aiAssistant.voice.correctionHighlightHint" })
            : isStreaming
              ? intl.formatMessage({ id: "aiAssistant.inputDraftWhileStreamingHint" })
              : !voiceprintEnabled || selectedVoiceprintId
                ? intl.formatMessage({ id: "aiAssistant.inputShortcutHint" })
                : intl.formatMessage({
                    id: "aiAssistant.voiceprint.selectRequiredHint",
                  })}
        </p>
      </div>
    </div>
  );
}
