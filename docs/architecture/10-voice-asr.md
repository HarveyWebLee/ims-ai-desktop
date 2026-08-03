# 10 — 语音转写与按段纠错

> 编码依据。语音是 **chat 前处理**，不进入 LangGraph / SSE 对话主链。  
> 纠错算法细节（词典 / Qdrant / LLM）与知识库关系见 [`05-qdrant-rag.md`](./05-qdrant-rag.md) §5.1。

## 1. 目标

1. **边说边出字**：Realtime ASR（DashScope）按 Server VAD 切段，词级 / 句级回显。
2. **按段并发纠错**：每段 ASR 落定后立即异步跑多级纠错；纠错相对 ASR **略滞后**，与后续段识别并行。
3. **段序与映射**：每段有稳定 `seq`，纠错结果写回该段；展示按 `seq` 拼接，乱序完成不打乱顺序。
4. **实时回显**：`partial`（当前句 ASR）与 `segment(done)`（该段纠错结果）均立即推送桌面并写入输入框；纠错相对 ASR 可略滞后，但不攒到停录。
5. **无终稿整段再纠**：停录后只等待 in-flight 段纠错结束并拼接，**不再**对全文跑一次 `multi_stage_correct`。
6. **纠错可视化（可选）**：配置开关开启时，输入框对被纠错的字/句/段加下划线，悬停显示纠错前原文；关闭时仅普通文本。

## 2. 非目标

- 对每一个未落定的 `partial` 预览跑纠错（易抖、易打爆检索/LLM）
- 停录后再做全文二次纠错
- 旧版「仅 final 整段纠错」协议兼容
- 声纹参与 ASR/纠错算法（声纹只做前端门禁）

## 3. 总体数据流

```text
麦克风 PCM
  →（可选声纹门禁：不匹配则不上行）
  → Agent WS 桥接 → DashScope Realtime ASR
  → VAD 落定一句 → segment(seq, raw, status=pending)
  → 线程池 / to_thread：multi_stage_correct(raw, context=前序已定稿)
  → segment(seq, text, raw, stage, changed, status=done)
  → 桌面：committed[seq] 更新 + 当前句 partial 预览
  → stop → 等待 in-flight → final(text, segments[])（仅汇总）
  → 写入输入框；用户发送 → 普通 chat
```

降级（Realtime 不可用）：

| 模式      | 行为                                                                                  |
| --------- | ------------------------------------------------------------------------------------- |
| HTTP 分片 | 累计缓冲并行 ASR+纠错；finish 取最高 seq 结果，拆成 `segments` 回传（不再额外全文纠） |
| Oneshot   | 整段一次 ASR+纠错，单元素 `segments`                                                  |

## 4. Realtime WebSocket 协议

路径：`WS /api/agent/transcribe/realtime`（桌面经 Vite 同源代理到 Agent `:8008`）。

### 4.1 客户端 → 服务端

| type    | 字段                | 说明                                       |
| ------- | ------------------- | ------------------------------------------ |
| `audio` | `data` base64 PCM16 | 16kHz mono                                 |
| `stop`  | —                   | 结束会话，触发上游 `session.finish` 并收尾 |

### 4.2 服务端 → 客户端

| type      | 字段                                                | 说明                                                     |
| --------- | --------------------------------------------------- | -------------------------------------------------------- |
| `ready`   | `model`                                             | 会话就绪                                                 |
| `partial` | `preview`                                           | **仅当前未落定句**的 ASR 预览（`text+stash`）            |
| `segment` | `seq`, `raw`, `text`, `status`, `changed`, `stage?` | 段状态。`pending`：刚落定，`text==raw`；`done`：纠错完成 |
| `final`   | `text`, `segments[]`                                | 停录后汇总；**不**再跑全文纠错                           |
| `error`   | `message`                                           | 失败                                                     |

`segments[]` 元素：

```json
{
  "seq": 0,
  "raw": "打开冷动水泵",
  "text": "打开冷冻水泵",
  "stage": "dictionary",
  "changed": true,
  "status": "done"
}
```

### 4.3 展示拼接规则（桌面）

```text
display = join(segments[i].text for i in order) + partial.preview
```

中文段之间 **不插入空格**。录音开始前已有键盘文案时，语音结果拼在其后（与既有输入框行为一致）。

## 5. 按段纠错

### 5.1 触发点

- **仅** DashScope `conversation.item.input_audio_transcription.completed`（VAD 落定句）触发纠错任务。
- `partial` 只更新预览，不纠错。

### 5.2 并发与顺序

- 每段独立 `asyncio.to_thread(multi_stage_correct, ...)`（或等价线程池）。
- 段 N 的纠错可与段 N+1 的 ASR / 纠错重叠。
- 结果按 `seq` 写回映射表；UI 只按序读映射，保证不乱。

### 5.3 上下文

- 纠错输入仍是 **本段 `raw`**（保证段映射清晰）。
- 检索 / LLM 可带 **前序已 `done` 段的 `text` 拼接** 作 `context`，缓解跨段专名，但输出仍只替换本段。

### 5.4 停录收尾

1. 发 `stop` → 上游 finish。
2. 若尚有未 `completed` 的当前预览：升为最后一段并纠错（或作为 `pending` 段纳入等待）。
3. `asyncio.gather` 等待 in-flight（有上限超时）；超时段用 `raw` 落 `done`。
4. 推送 `final`，关闭连接。

### 5.5 多级算法（不变）

`Rule → Redis Cache → Dictionary → Vector → LLM`，低成本优先退出；fail-open。实现：`app/services/voice/pipeline.py`。

## 6. 纠错可视化开关

| 项   | 说明                                                                            |
| ---- | ------------------------------------------------------------------------------- |
| 位置 | 桌面端设置页（持久化本地 Store）                                                |
| 键   | `voiceCorrectionHighlightEnabled`（默认 `false`）                               |
| 开   | 对被纠错段（`changed===true`）在输入区用**下划线**标注；悬停 Tooltip 显示 `raw` |
| 关   | 输入区仅普通文本，无下划线 / 无悬停原文                                         |

开关 **只影响展示**，不影响 ASR/纠错管线。手动改输入框正文后清除本轮段标注（避免映射错位）。

实现要点：带标注层（backdrop + 透明 TextArea，或等价可编辑方案）；发送 chat 仍用纯文本 `text`。

## 7. 声纹门禁（解耦）

- 未选 / 不匹配：不上行 PCM。
- 唯一开关：Agent `VOICEPRINT_ENABLED`；桌面启动时拉 `GET /api/agent/voiceprints/config` 同步 UI 门禁。
- 生产级声纹（预处理 / ERes2Net-Large / Qdrant 多模板 / 1:1·1:N）见 [`11-voiceprint.md`](./11-voiceprint.md)。

## 8. 配置

Agent（纠错能力）：

```bash
TRANSCRIBE_REALTIME_ENABLED=true
TRANSCRIBE_REALTIME_MODEL=qwen3-asr-flash-realtime
TRANSCRIBE_RAG_ENABLED=true
TRANSCRIBE_DICTIONARY_ENABLED=true
# … 其余 TRANSCRIBE_CORRECT_* 见 05 §5.1 / .env.example
```

桌面（可视化）：

- Store：`voiceCorrectionHighlightEnabled`
- 设置页开关文案：`aiAssistant.settings.voiceCorrectionHighlight*`

## 9. 关键实现

| 层           | 路径                                                                          |
| ------------ | ----------------------------------------------------------------------------- |
| Realtime 桥  | `app/services/voice/realtime_bridge.py`                                       |
| 纠错管线     | `app/services/voice/pipeline.py` 及 rules/cache/dictionary/semantic/llm_stage |
| HTTP/Oneshot | `transcription.py` / `stream_session.py` / `api/transcribe.py`                |
| 桌面采集     | `apps/desktop/.../VoiceInput.tsx`                                             |
| 输入与标注   | `MessageInput.tsx` + Store + Settings                                         |
| 测试         | `tests/test_realtime_bridge.py` 等                                            |

## 10. 验收要点

- [ ] 多句连续说话：每句落定后输入框先出 ASR，随后该段被替换为纠错文（可感知滞后）
- [ ] 段序正确，后句不覆盖前句
- [ ] 停录后无「全文再纠」导致的二次跳变（仅可能有 in-flight 段补齐）
- [ ] 高亮开关开：纠错处有下划线，悬停见原文；关：纯文本
- [ ] 发送内容为当前输入框纯文本，进入普通 chat
