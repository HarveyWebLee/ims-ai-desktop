/**
 * 语音输入：优先 Realtime ASR（PCM → WS partial 词级回显），失败降级 HTTP 分片并行。
 * 停止后终稿走多级纠错；录音中用 Analyser 驱动话筒音量闪烁。
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { Button, Tooltip } from "antd";
import { message } from "@/antd/feedback";
import { AudioFilled, AudioOutlined, LoadingOutlined } from "@ant-design/icons";
import { useIntl } from "react-intl";
import {
  transcribeAudio,
  transcribeStreamChunk,
  transcribeStreamFinish,
  transcribeStreamStart,
  verifyVoiceprint,
} from "@/services/AgentController";
import { getCatalogItem } from "@ims/agent-core/model-catalog";
import type { AgentModelId } from "@ims/shared-types";
import { useAiAssistantStore } from "./store";
import styles from "./index.module.less";

const MAX_RECORD_MS = 60_000;
const STREAM_CHUNK_MS = 1200;
/** 音量可视化增益：越大说话时图标动效越明显 */
const VOLUME_GAIN = 9;
const TARGET_SAMPLE_RATE = 16000;
/** 连续无有效语音（音量/识别文本）超时后自动结束并纠错 */
const SILENCE_TIMEOUT_MS = 10_000;
/** 录音中声纹实时核验间隔 */
const VOICEPRINT_LIVE_CHECK_MS = 1000;
/** 实时核验最少有效 PCM（秒）；过短易误伤本人 */
const VOICEPRINT_LIVE_MIN_SEC = 1.2;
/** 实时核验滑动窗（秒） */
const VOICEPRINT_LIVE_WINDOW_SEC = 2.5;
/** 关闭门禁相对阈值的滞后，减少来回抖动 */
const VOICEPRINT_LIVE_CLOSE_MARGIN = 0.05;
/** 滤除提示最小间隔 */
const VOICEPRINT_FILTER_HINT_MS = 4000;
/**
 * 视为「有效说话」的 RMS 阈值（经 VOLUME_GAIN 后）。
 * 过低会被环境底噪一直刷新计时，导致 10s 永不触发；偏高只影响静音判定，不影响动效曲线。
 */
const SPEECH_ACTIVITY_THRESHOLD = 0.32;
/** 涟漪「正在说话」视觉阈值，可低于活动阈值 */
const SPEECH_VISUAL_THRESHOLD = 0.14;

function pickMimeType(): string | undefined {
  const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"];
  for (const type of candidates) {
    if (typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(type)) {
      return type;
    }
  }
  return undefined;
}

function mimeToExtension(mime?: string): string {
  if (!mime) return "webm";
  if (mime.includes("mp4")) return "m4a";
  if (mime.includes("ogg")) return "ogg";
  return "webm";
}

function floatTo16BitPCM(input: Float32Array, inputSampleRate: number): Int16Array {
  if (inputSampleRate === TARGET_SAMPLE_RATE) {
    const out = new Int16Array(input.length);
    for (let i = 0; i < input.length; i += 1) {
      const s = Math.max(-1, Math.min(1, input[i]));
      out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    return out;
  }
  const ratio = inputSampleRate / TARGET_SAMPLE_RATE;
  const newLen = Math.max(1, Math.floor(input.length / ratio));
  const out = new Int16Array(newLen);
  for (let i = 0; i < newLen; i += 1) {
    const idx = Math.min(input.length - 1, Math.floor(i * ratio));
    const s = Math.max(-1, Math.min(1, input[idx]));
    out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return out;
}

function int16ToBase64(samples: Int16Array): string {
  const bytes = new Uint8Array(samples.buffer, samples.byteOffset, samples.byteLength);
  let binary = "";
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
  }
  return btoa(binary);
}

function buildRealtimeWsUrl(): string {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}/api/agent/transcribe/realtime`;
}

type VoicePhase = "idle" | "recording" | "transcribing";
type CaptureMode = "realtime" | "http-chunk" | "oneshot";

/** 语音终稿纠错元信息（供输入区展示 ASR→纠正） */
export type VoiceCorrectionMeta = {
  raw?: string;
  stage?: string;
  changed?: boolean;
};

type VoiceFinalPayload = VoiceCorrectionMeta & { text: string };

export default function VoiceInput({
  onTranscribed,
  onInterim,
  onRecordingStart,
  disabled = false,
}: {
  onTranscribed: (text: string, meta?: VoiceCorrectionMeta) => void;
  onInterim?: (text: string) => void;
  onRecordingStart?: () => void;
  disabled?: boolean;
}) {
  const intl = useIntl();
  const { selectedModelId, selectedVoiceprintId } = useAiAssistantStore();
  const [phase, setPhase] = useState<VoicePhase>("idle");
  const [elapsedSec, setElapsedSec] = useState(0);
  const [interimText, setInterimText] = useState("");

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const stopTimerRef = useRef<number | null>(null);
  const elapsedTimerRef = useRef<number | null>(null);
  const mimeTypeRef = useRef<string | undefined>(undefined);
  const startedAtRef = useRef(0);
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const rafRef = useRef<number | null>(null);
  const meterElRef = useRef<HTMLSpanElement | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const seqRef = useRef(0);
  const inflightRef = useRef<Promise<unknown>[]>([]);
  const modeRef = useRef<CaptureMode>("realtime");
  const wsRef = useRef<WebSocket | null>(null);
  const finalTextRef = useRef<VoiceFinalPayload | null>(null);
  const finalWaitersRef = useRef<Array<(payload: VoiceFinalPayload) => void>>([]);
  const lastPartialRef = useRef("");
  const lastActivityAtRef = useRef(0);
  const silenceWatchRef = useRef<number | null>(null);
  const stoppingRef = useRef(false);
  const stopRecordingRef = useRef<() => void>(() => undefined);
  /** 声纹核验用 PCM 缓冲（Int16 @16k） */
  const pcmVerifyChunksRef = useRef<Int16Array[]>([]);
  const pcmCaptureNodesRef = useRef<{
    ctx: AudioContext;
    source: MediaStreamAudioSourceNode;
    processor: ScriptProcessorNode;
  } | null>(null);
  /** 当前是否放行 ASR（匹配中）；不匹配时继续录音但不送识别 */
  const voiceprintLiveOkRef = useRef(false);
  /** 本轮是否曾匹配成功（停录时判断是否有可采纳内容） */
  const voiceprintEverMatchedRef = useRef(false);
  /** 匹配时段已采纳的 interim，滤除时回滚到此 */
  const matchedInterimRef = useRef("");
  const voiceprintVerifyInflightRef = useRef(false);
  const liveVoiceprintTimerRef = useRef<number | null>(null);
  const filterHintAtRef = useRef(0);

  const clearElapsedTimer = useCallback(() => {
    if (elapsedTimerRef.current) {
      window.clearInterval(elapsedTimerRef.current);
      elapsedTimerRef.current = null;
    }
  }, []);

  const clearSilenceWatch = useCallback(() => {
    if (silenceWatchRef.current) {
      window.clearInterval(silenceWatchRef.current);
      silenceWatchRef.current = null;
    }
  }, []);

  const clearLiveVoiceprintWatch = useCallback(() => {
    if (liveVoiceprintTimerRef.current) {
      window.clearInterval(liveVoiceprintTimerRef.current);
      liveVoiceprintTimerRef.current = null;
    }
  }, []);

  const noteVoiceActivity = useCallback(() => {
    lastActivityAtRef.current = Date.now();
  }, []);

  const applyVoiceLevel = useCallback((level: number) => {
    const el = meterElRef.current;
    if (!el) return;
    el.style.setProperty("--voice-level", level.toFixed(3));
    el.dataset.speaking = level >= SPEECH_VISUAL_THRESHOLD ? "1" : "0";
    // 仅较高电平才刷新静音计时，避免底噪拖住超时
    if (level >= SPEECH_ACTIVITY_THRESHOLD) {
      lastActivityAtRef.current = Date.now();
    }
  }, []);

  const stopVolumeMeter = useCallback(() => {
    if (rafRef.current != null) {
      window.cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    const el = meterElRef.current;
    if (el) {
      el.style.setProperty("--voice-level", "0");
      el.dataset.speaking = "0";
    }
  }, []);

  const teardownAudioGraph = useCallback(() => {
    stopVolumeMeter();
    try {
      processorRef.current?.disconnect();
    } catch {
      /* ignore */
    }
    try {
      sourceNodeRef.current?.disconnect();
    } catch {
      /* ignore */
    }
    processorRef.current = null;
    sourceNodeRef.current = null;
    const ctx = audioContextRef.current;
    audioContextRef.current = null;
    if (ctx) {
      void ctx.close().catch(() => undefined);
    }
  }, [stopVolumeMeter]);

  const cleanupMic = useCallback(() => {
    if (stopTimerRef.current) {
      window.clearTimeout(stopTimerRef.current);
      stopTimerRef.current = null;
    }
    clearElapsedTimer();
    clearSilenceWatch();
    clearLiveVoiceprintWatch();
    teardownAudioGraph();
    const pcmNodes = pcmCaptureNodesRef.current;
    pcmCaptureNodesRef.current = null;
    if (pcmNodes) {
      try {
        pcmNodes.processor.disconnect();
        pcmNodes.source.disconnect();
      } catch {
        /* ignore */
      }
      void pcmNodes.ctx.close().catch(() => undefined);
    }
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    mediaRecorderRef.current = null;
    chunksRef.current = [];
    pcmVerifyChunksRef.current = [];
  }, [clearElapsedTimer, clearLiveVoiceprintWatch, clearSilenceWatch, teardownAudioGraph]);

  const appendVerifyPcm = useCallback((pcm: Int16Array) => {
    if (!pcm.length) return;
    const buf = pcmVerifyChunksRef.current;
    buf.push(pcm);
    // 最多保留约 4 秒 @16k，避免内存膨胀
    let total = buf.reduce((n, c) => n + c.length, 0);
    const maxSamples = TARGET_SAMPLE_RATE * 4;
    while (total > maxSamples && buf.length > 1) {
      const removed = buf.shift();
      total -= removed?.length ?? 0;
    }
  }, []);

  const buildVerifyPcmBlob = useCallback(
    (opts?: { windowSec?: number; minSec?: number }): Blob | null => {
      const chunks = pcmVerifyChunksRef.current;
      if (!chunks.length) return null;
      const total = chunks.reduce((n, c) => n + c.length, 0);
      const minSec = opts?.minSec ?? 0.6;
      if (total < TARGET_SAMPLE_RATE * minSec) return null;
      const merged = new Int16Array(total);
      let offset = 0;
      for (const c of chunks) {
        merged.set(c, offset);
        offset += c.length;
      }
      const windowSec = opts?.windowSec;
      if (windowSec && windowSec > 0) {
        const maxSamples = Math.floor(TARGET_SAMPLE_RATE * windowSec);
        if (merged.length > maxSamples) {
          const windowed = merged.subarray(merged.length - maxSamples);
          const copy = new Int16Array(windowed.length);
          copy.set(windowed);
          return new Blob([copy.buffer], { type: "application/octet-stream" });
        }
      }
      return new Blob([merged.buffer], { type: "application/octet-stream" });
    },
    [],
  );

  const startPcmCaptureForVerify = useCallback(
    async (stream: MediaStream) => {
      const AudioCtx =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      if (ctx.state === "suspended") await ctx.resume();
      const source = ctx.createMediaStreamSource(stream);
      const processor = ctx.createScriptProcessor(4096, 1, 1);
      processor.onaudioprocess = (e) => {
        const input = e.inputBuffer.getChannelData(0);
        appendVerifyPcm(floatTo16BitPCM(input, ctx.sampleRate));
      };
      source.connect(processor);
      const mute = ctx.createGain();
      mute.gain.value = 0;
      processor.connect(mute);
      mute.connect(ctx.destination);
      pcmCaptureNodesRef.current = { ctx, source, processor };
    },
    [appendVerifyPcm],
  );

  const gateByVoiceprint = useCallback(async (): Promise<boolean> => {
    if (!selectedVoiceprintId) {
      message.warning(intl.formatMessage({ id: "aiAssistant.voiceprint.selectRequired" }));
      return false;
    }
    const blob = buildVerifyPcmBlob();
    if (!blob) {
      message.warning(intl.formatMessage({ id: "aiAssistant.voiceprint.audioTooShort" }));
      return false;
    }
    try {
      const result = await verifyVoiceprint(selectedVoiceprintId, blob, {
        sampleRate: TARGET_SAMPLE_RATE,
      });
      if (result.skipped) return true;
      if (!result.matched) {
        message.error(
          intl.formatMessage(
            { id: "aiAssistant.voiceprint.mismatch" },
            {
              score: result.score,
              threshold: result.threshold,
              name: result.display_name || "",
            },
          ),
        );
        return false;
      }
      return true;
    } catch (err) {
      message.error(
        intl.formatMessage(
          { id: "aiAssistant.voiceprint.verifyFailed" },
          { error: err instanceof Error ? err.message : String(err) },
        ),
      );
      return false;
    }
  }, [buildVerifyPcmBlob, intl, selectedVoiceprintId]);

  const applyVoiceprintGate = useCallback(
    (open: boolean, opts?: { score?: number; threshold?: number }) => {
      const wasOpen = voiceprintLiveOkRef.current;
      if (open) {
        voiceprintLiveOkRef.current = true;
        voiceprintEverMatchedRef.current = true;
        if (!wasOpen && matchedInterimRef.current) {
          setInterimText(matchedInterimRef.current);
          onInterim?.(matchedInterimRef.current);
        }
        return;
      }
      // 关闭：停止送 ASR，输入框回滚到已匹配内容
      voiceprintLiveOkRef.current = false;
      lastPartialRef.current = matchedInterimRef.current;
      setInterimText(matchedInterimRef.current);
      onInterim?.(matchedInterimRef.current);
      if (wasOpen) {
        const now = Date.now();
        if (now - filterHintAtRef.current >= VOICEPRINT_FILTER_HINT_MS) {
          filterHintAtRef.current = now;
          message.info(
            intl.formatMessage(
              { id: "aiAssistant.voiceprint.filteredKeepListening" },
              {
                score: opts?.score ?? "-",
                threshold: opts?.threshold ?? "-",
              },
            ),
          );
        }
      }
    },
    [intl, onInterim],
  );

  const runLiveVoiceprintCheck = useCallback(async () => {
    if (stoppingRef.current) return;
    if (!selectedVoiceprintId || voiceprintVerifyInflightRef.current) return;
    const blob = buildVerifyPcmBlob({
      windowSec: VOICEPRINT_LIVE_WINDOW_SEC,
      minSec: VOICEPRINT_LIVE_MIN_SEC,
    });
    if (!blob) return;
    voiceprintVerifyInflightRef.current = true;
    try {
      const result = await verifyVoiceprint(selectedVoiceprintId, blob, {
        sampleRate: TARGET_SAMPLE_RATE,
      });
      if (stoppingRef.current) return;
      if (result.skipped) {
        applyVoiceprintGate(true);
        return;
      }
      const score = Number(result.score);
      const threshold = Number(result.threshold);
      if (voiceprintLiveOkRef.current) {
        // 已放行：仅明显低于阈值才关闭，避免本人短窗抖动被滤掉
        if (score < threshold - VOICEPRINT_LIVE_CLOSE_MARGIN) {
          applyVoiceprintGate(false, { score, threshold });
        }
      } else if (score >= threshold) {
        applyVoiceprintGate(true);
      }
      // 未放行且未达阈值：保持滤除，继续录音，不中断
    } catch (err) {
      if (stoppingRef.current) return;
      console.warn("live voiceprint verify failed", err);
    } finally {
      voiceprintVerifyInflightRef.current = false;
    }
  }, [applyVoiceprintGate, buildVerifyPcmBlob, selectedVoiceprintId]);

  const startLiveVoiceprintWatch = useCallback(() => {
    clearLiveVoiceprintWatch();
    liveVoiceprintTimerRef.current = window.setInterval(() => {
      void runLiveVoiceprintCheck();
    }, VOICEPRINT_LIVE_CHECK_MS);
    window.setTimeout(
      () => {
        void runLiveVoiceprintCheck();
      },
      Math.floor(VOICEPRINT_LIVE_MIN_SEC * 1000),
    );
  }, [clearLiveVoiceprintWatch, runLiveVoiceprintCheck]);

  useEffect(() => () => cleanupMic(), [cleanupMic]);

  const resolveModelId = useCallback((): AgentModelId | undefined => {
    const catalog = getCatalogItem(selectedModelId);
    return catalog?.supportsAudio ? selectedModelId : undefined;
  }, [selectedModelId]);

  const pushInterim = useCallback(
    (text: string) => {
      if (!text?.trim()) return;
      const next = text.trim();
      if (next !== lastPartialRef.current) {
        noteVoiceActivity();
      }
      lastPartialRef.current = next;
      // 仅匹配时段写入输入框；不匹配时段直接滤掉
      if (!voiceprintLiveOkRef.current) return;
      matchedInterimRef.current = next;
      setInterimText(next);
      onInterim?.(next);
    },
    [noteVoiceActivity, onInterim],
  );

  const resolveFinal = useCallback((payload: VoiceFinalPayload | string) => {
    const next: VoiceFinalPayload = typeof payload === "string" ? { text: payload } : payload;
    finalTextRef.current = next;
    const waiters = finalWaitersRef.current;
    finalWaitersRef.current = [];
    waiters.forEach((w) => w(next));
  }, []);

  const waitForFinal = useCallback(
    (timeoutMs = 12000) =>
      new Promise<VoiceFinalPayload>((resolve) => {
        if (finalTextRef.current != null) {
          resolve(finalTextRef.current);
          return;
        }
        const timer = window.setTimeout(() => {
          resolve({ text: lastPartialRef.current || "" });
        }, timeoutMs);
        finalWaitersRef.current.push((payload) => {
          window.clearTimeout(timer);
          resolve(payload);
        });
      }),
    [],
  );

  /** Realtime：PCM → WS */
  const startRealtimeCapture = useCallback(
    async (stream: MediaStream) => {
      const ws = new WebSocket(buildRealtimeWsUrl());
      wsRef.current = ws;
      finalTextRef.current = null;
      lastPartialRef.current = "";

      await new Promise<void>((resolve, reject) => {
        const timer = window.setTimeout(() => reject(new Error("ws timeout")), 8000);
        ws.onopen = () => {
          /* wait ready */
        };
        ws.onerror = () => {
          window.clearTimeout(timer);
          reject(new Error("ws error"));
        };
        ws.onmessage = (ev) => {
          try {
            const data = JSON.parse(String(ev.data)) as {
              type?: string;
              text?: string;
              message?: string;
              raw?: string;
              stage?: string;
              changed?: boolean;
            };
            if (data.type === "ready") {
              window.clearTimeout(timer);
              resolve();
            } else if (data.type === "partial" && data.text) {
              pushInterim(data.text);
            } else if (data.type === "completed" && data.text) {
              pushInterim(data.text);
            } else if (data.type === "final") {
              resolveFinal({
                text: data.text || "",
                raw: data.raw,
                stage: data.stage,
                changed: data.changed,
              });
            } else if (data.type === "error") {
              window.clearTimeout(timer);
              reject(new Error(data.message || "realtime error"));
            }
          } catch {
            /* ignore */
          }
        };
      });

      // 继续监听后续 partial/final
      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(String(ev.data)) as {
            type?: string;
            text?: string;
            message?: string;
            raw?: string;
            stage?: string;
            changed?: boolean;
          };
          if (data.type === "partial" && data.text) {
            pushInterim(data.text);
          } else if (data.type === "completed" && data.text) {
            pushInterim(data.text);
          } else if (data.type === "final") {
            resolveFinal({
              text: data.text || "",
              raw: data.raw,
              stage: data.stage,
              changed: data.changed,
            });
          } else if (data.type === "error") {
            message.error(
              intl.formatMessage(
                { id: "aiAssistant.voice.transcribeFailed" },
                { error: data.message || "error" },
              ),
            );
            resolveFinal({ text: lastPartialRef.current || "" });
          }
        } catch {
          /* ignore */
        }
      };

      const AudioCtx =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      if (!AudioCtx) {
        throw new Error("AudioContext unsupported");
      }
      const ctx = new AudioCtx();
      audioContextRef.current = ctx;
      if (ctx.state === "suspended") {
        await ctx.resume();
      }
      const source = ctx.createMediaStreamSource(stream);
      sourceNodeRef.current = source;
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.65;
      source.connect(analyser);
      const samples = new Uint8Array(analyser.fftSize);
      const tick = () => {
        if (ctx.state === "closed") return;
        analyser.getByteTimeDomainData(samples);
        let sum = 0;
        for (let i = 0; i < samples.length; i += 1) {
          const n = (samples[i] - 128) / 128;
          sum += n * n;
        }
        const level = Math.min(1, Math.max(0, Math.sqrt(sum / samples.length) * VOLUME_GAIN));
        applyVoiceLevel(level);
        rafRef.current = window.requestAnimationFrame(tick);
      };
      rafRef.current = window.requestAnimationFrame(tick);

      const processor = ctx.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;
      processor.onaudioprocess = (e) => {
        const input = e.inputBuffer.getChannelData(0);
        const pcm = floatTo16BitPCM(input, ctx.sampleRate);
        if (!pcm.length) return;
        appendVerifyPcm(pcm);
        // 不匹配时段不送 ASR，相当于滤掉该段语音
        if (!voiceprintLiveOkRef.current) return;
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
        wsRef.current.send(
          JSON.stringify({
            type: "audio",
            data: int16ToBase64(pcm),
          }),
        );
      };
      source.connect(processor);
      // 接到静音节点，避免麦克风回放到扬声器
      const mute = ctx.createGain();
      mute.gain.value = 0;
      processor.connect(mute);
      mute.connect(ctx.destination);
    },
    [appendVerifyPcm, applyVoiceLevel, intl, pushInterim, resolveFinal],
  );

  const enqueueHttpChunk = useCallback(
    (blob: Blob) => {
      if (!voiceprintLiveOkRef.current) return;
      const sessionId = sessionIdRef.current;
      if (!sessionId || blob.size <= 0) return;
      const seq = seqRef.current;
      seqRef.current += 1;
      const mime = mimeTypeRef.current || blob.type || "audio/webm";
      const task = transcribeStreamChunk(blob, {
        sessionId,
        seq,
        modelId: resolveModelId(),
        filename: `chunk-${seq}.${mimeToExtension(mime)}`,
      })
        .then((res) => {
          if (res.interim_text) pushInterim(res.interim_text);
        })
        .catch(() => undefined);
      inflightRef.current.push(task);
    },
    [pushInterim, resolveModelId],
  );

  const startHttpChunkCapture = useCallback(
    async (stream: MediaStream) => {
      const started = await transcribeStreamStart({
        modelId: resolveModelId(),
      });
      sessionIdRef.current = started.session_id;
      const mimeType = pickMimeType();
      mimeTypeRef.current = mimeType;
      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size <= 0) return;
        chunksRef.current.push(e.data);
        enqueueHttpChunk(e.data);
      };
      recorder.start(STREAM_CHUNK_MS);
      mediaRecorderRef.current = recorder;

      // 简易音量
      const AudioCtx =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      if (AudioCtx) {
        const ctx = new AudioCtx();
        audioContextRef.current = ctx;
        const source = ctx.createMediaStreamSource(stream);
        sourceNodeRef.current = source;
        const analyser = ctx.createAnalyser();
        analyser.fftSize = 256;
        source.connect(analyser);
        const samples = new Uint8Array(analyser.fftSize);
        const tick = () => {
          if (ctx.state === "closed") return;
          analyser.getByteTimeDomainData(samples);
          let sum = 0;
          for (let i = 0; i < samples.length; i += 1) {
            const n = (samples[i] - 128) / 128;
            sum += n * n;
          }
          const level = Math.min(1, Math.max(0, Math.sqrt(sum / samples.length) * VOLUME_GAIN));
          applyVoiceLevel(level);
          rafRef.current = window.requestAnimationFrame(tick);
        };
        rafRef.current = window.requestAnimationFrame(tick);
      }
    },
    [applyVoiceLevel, enqueueHttpChunk, resolveModelId],
  );

  const finishCapture = useCallback(async () => {
    clearLiveVoiceprintWatch();
    setPhase("transcribing");
    try {
      // 本轮从未匹配成功：终验兜底；已匹配过则采信门禁期内送入 ASR 的内容
      if (!voiceprintEverMatchedRef.current) {
        const allowed = await gateByVoiceprint();
        if (!allowed) {
          onTranscribed("");
          return;
        }
        voiceprintLiveOkRef.current = true;
        voiceprintEverMatchedRef.current = true;
      }

      if (modeRef.current === "realtime") {
        const ws = wsRef.current;
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "stop" }));
        }
        const finalPayload = await waitForFinal(15000);
        wsRef.current?.close();
        wsRef.current = null;
        const text = (finalPayload.text.trim() || matchedInterimRef.current).trim();
        onTranscribed(text, {
          raw: finalPayload.raw,
          stage: finalPayload.stage,
          changed: finalPayload.changed,
        });
        return;
      }

      if (modeRef.current === "http-chunk") {
        const recorder = mediaRecorderRef.current;
        if (recorder && recorder.state !== "inactive") {
          await new Promise<void>((resolve) => {
            recorder.onstop = () => resolve();
            recorder.stop();
          });
        }
        await Promise.allSettled(inflightRef.current);
        inflightRef.current = [];
        const sessionId = sessionIdRef.current;
        if (sessionId) {
          const result = await transcribeStreamFinish(sessionId);
          sessionIdRef.current = null;
          onTranscribed(result.text?.trim() ?? "", {
            raw: result.raw,
            stage: result.stage,
            changed: result.changed,
          });
          return;
        }
      }

      const mime = mimeTypeRef.current || "audio/webm";
      const blob = new Blob(chunksRef.current, { type: mime });
      if (!blob.size) {
        message.warning(intl.formatMessage({ id: "aiAssistant.voice.emptyRecording" }));
        onTranscribed("");
        return;
      }
      const result = await transcribeAudio(blob, {
        modelId: resolveModelId(),
        filename: `recording.${mimeToExtension(mime)}`,
      });
      onTranscribed(result.text?.trim() ?? "", {
        raw: result.raw,
        stage: result.stage,
        changed: result.changed,
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      message.error(
        intl.formatMessage({ id: "aiAssistant.voice.transcribeFailed" }, { error: msg }),
      );
      onTranscribed(lastPartialRef.current || "");
    } finally {
      try {
        wsRef.current?.close();
      } catch {
        /* ignore */
      }
      cleanupMic();
      sessionIdRef.current = null;
      wsRef.current = null;
      stoppingRef.current = false;
      setPhase("idle");
      setElapsedSec(0);
      setInterimText("");
    }
  }, [
    cleanupMic,
    clearLiveVoiceprintWatch,
    gateByVoiceprint,
    intl,
    onTranscribed,
    resolveModelId,
    waitForFinal,
  ]);

  const stopRecording = useCallback(() => {
    if (stoppingRef.current) return;
    stoppingRef.current = true;
    clearElapsedTimer();
    clearSilenceWatch();
    clearLiveVoiceprintWatch();
    // realtime：先停采集图，再 finish；http：finish 里 stop recorder
    if (modeRef.current === "realtime") {
      teardownAudioGraph();
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    void finishCapture();
  }, [
    clearElapsedTimer,
    clearLiveVoiceprintWatch,
    clearSilenceWatch,
    finishCapture,
    teardownAudioGraph,
  ]);

  stopRecordingRef.current = stopRecording;

  const startSilenceWatch = useCallback(() => {
    clearSilenceWatch();
    noteVoiceActivity();
    silenceWatchRef.current = window.setInterval(() => {
      if (stoppingRef.current) return;
      if (Date.now() - lastActivityAtRef.current < SILENCE_TIMEOUT_MS) return;
      clearSilenceWatch();
      message.info(intl.formatMessage({ id: "aiAssistant.voice.idleTimeout" }));
      stopRecordingRef.current();
    }, 400);
  }, [clearSilenceWatch, intl, noteVoiceActivity]);

  const startRecording = useCallback(async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      message.error(intl.formatMessage({ id: "aiAssistant.voice.notSupported" }));
      return;
    }
    if (!selectedVoiceprintId) {
      message.warning(intl.formatMessage({ id: "aiAssistant.voiceprint.selectRequired" }));
      return;
    }
    try {
      stoppingRef.current = false;
      modeRef.current = "realtime";
      sessionIdRef.current = null;
      seqRef.current = 0;
      inflightRef.current = [];
      setInterimText("");
      lastPartialRef.current = "";
      finalTextRef.current = null;
      pcmVerifyChunksRef.current = [];
      voiceprintLiveOkRef.current = false;
      voiceprintEverMatchedRef.current = false;
      matchedInterimRef.current = "";
      voiceprintVerifyInflightRef.current = false;
      filterHintAtRef.current = 0;

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
      streamRef.current = stream;

      try {
        await startRealtimeCapture(stream);
        modeRef.current = "realtime";
      } catch {
        // 降级 HTTP 分片并行
        try {
          await startPcmCaptureForVerify(stream);
          await startHttpChunkCapture(stream);
          modeRef.current = "http-chunk";
        } catch {
          modeRef.current = "oneshot";
          await startPcmCaptureForVerify(stream);
          const mimeType = pickMimeType();
          mimeTypeRef.current = mimeType;
          const recorder = mimeType
            ? new MediaRecorder(stream, { mimeType })
            : new MediaRecorder(stream);
          chunksRef.current = [];
          recorder.ondataavailable = (e) => {
            if (e.data.size > 0) chunksRef.current.push(e.data);
          };
          recorder.start(250);
          mediaRecorderRef.current = recorder;

          // oneshot 也挂音量表，供动效与 10s 静音判定
          const AudioCtx =
            window.AudioContext ||
            (
              window as unknown as {
                webkitAudioContext?: typeof AudioContext;
              }
            ).webkitAudioContext;
          if (AudioCtx) {
            const ctx = new AudioCtx();
            audioContextRef.current = ctx;
            const source = ctx.createMediaStreamSource(stream);
            sourceNodeRef.current = source;
            const analyser = ctx.createAnalyser();
            analyser.fftSize = 256;
            source.connect(analyser);
            const samples = new Uint8Array(analyser.fftSize);
            const tick = () => {
              if (ctx.state === "closed") return;
              analyser.getByteTimeDomainData(samples);
              let sum = 0;
              for (let i = 0; i < samples.length; i += 1) {
                const n = (samples[i] - 128) / 128;
                sum += n * n;
              }
              applyVoiceLevel(
                Math.min(1, Math.max(0, Math.sqrt(sum / samples.length) * VOLUME_GAIN)),
              );
              rafRef.current = window.requestAnimationFrame(tick);
            };
            rafRef.current = window.requestAnimationFrame(tick);
          }
        }
      }

      startedAtRef.current = Date.now();
      setElapsedSec(0);
      setPhase("recording");
      onRecordingStart?.();
      startSilenceWatch();
      startLiveVoiceprintWatch();

      clearElapsedTimer();
      elapsedTimerRef.current = window.setInterval(() => {
        setElapsedSec(
          Math.min(
            Math.floor((Date.now() - startedAtRef.current) / 1000),
            Math.floor(MAX_RECORD_MS / 1000),
          ),
        );
      }, 250);

      stopTimerRef.current = window.setTimeout(() => {
        message.info(intl.formatMessage({ id: "aiAssistant.voice.maxDuration" }));
        stopRecording();
      }, MAX_RECORD_MS);
    } catch (err) {
      stoppingRef.current = false;
      cleanupMic();
      setPhase("idle");
      setElapsedSec(0);
      const name = err instanceof DOMException ? err.name : "";
      if (name === "NotAllowedError" || name === "PermissionDeniedError") {
        message.error(intl.formatMessage({ id: "aiAssistant.voice.permissionDenied" }));
      } else {
        message.error(intl.formatMessage({ id: "aiAssistant.voice.recordFailed" }));
      }
    }
  }, [
    applyVoiceLevel,
    cleanupMic,
    clearElapsedTimer,
    intl,
    onRecordingStart,
    selectedVoiceprintId,
    startHttpChunkCapture,
    startPcmCaptureForVerify,
    startRealtimeCapture,
    startSilenceWatch,
    startLiveVoiceprintWatch,
    stopRecording,
  ]);

  const busy = phase !== "idle";
  const handleClick = () => {
    if (disabled || phase === "transcribing") return;
    if (phase === "recording") {
      stopRecording();
    } else {
      void startRecording();
    }
  };

  const tooltipTitle =
    phase === "transcribing"
      ? intl.formatMessage({ id: "aiAssistant.voice.transcribing" })
      : phase === "recording"
        ? interimText
          ? intl.formatMessage(
              { id: "aiAssistant.voice.recordingInterim" },
              { seconds: elapsedSec, text: interimText },
            )
          : intl.formatMessage(
              { id: "aiAssistant.voice.recordingElapsed" },
              { seconds: elapsedSec },
            )
        : intl.formatMessage({ id: "aiAssistant.voice.startRecording" });

  const buttonClass =
    phase === "recording"
      ? styles.voiceBtnRecording
      : phase === "transcribing"
        ? styles.voiceBtnTranscribing
        : styles.voiceBtn;

  const icon =
    phase === "transcribing" ? (
      <LoadingOutlined spin />
    ) : phase === "recording" ? (
      <AudioFilled />
    ) : (
      <AudioOutlined />
    );

  const wrapClass =
    phase === "recording"
      ? `${styles.voiceBtnWrap} ${styles.voiceBtnWrapRecording}`
      : styles.voiceBtnWrap;

  return (
    <Tooltip title={tooltipTitle}>
      <span ref={meterElRef} className={wrapClass} data-speaking="0">
        <Button
          type="text"
          className={buttonClass}
          icon={icon}
          disabled={disabled}
          aria-disabled={disabled || phase === "transcribing"}
          aria-busy={busy}
          aria-pressed={phase === "recording"}
          onClick={handleClick}
          aria-label={tooltipTitle}
          shape="circle"
        />
      </span>
    </Tooltip>
  );
}
