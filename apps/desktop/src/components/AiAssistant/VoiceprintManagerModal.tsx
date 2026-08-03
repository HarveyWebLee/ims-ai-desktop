/**
 * 声纹库管理面板：多段录入向导（≥3 段 enrolled）
 */
import { useCallback, useEffect, useRef, useState } from "react";
import {
  Button,
  Empty,
  Form,
  Input,
  Modal,
  Popconfirm,
  Progress,
  Select,
  Space,
  Table,
  Tag,
  Tooltip,
} from "antd";
import { AudioOutlined, DeleteOutlined, EditOutlined, PlusOutlined } from "@ant-design/icons";
import { useIntl } from "react-intl";
import { message } from "@/antd/feedback";
import * as AgentController from "@/services/AgentController";
import type { VoiceprintProfile } from "@/services/AgentController";

const TARGET_SR = 16000;
/** 单段录入时长：服务端要求有效语音约 ≥8s */
const ENROLL_MS = 10000;
const ENROLL_MIN_DEFAULT = 3;
const ENROLL_MAX_DEFAULT = 5;

function floatTo16BitPCM(input: Float32Array, inputSampleRate: number): Int16Array {
  if (inputSampleRate === TARGET_SR) {
    const out = new Int16Array(input.length);
    for (let i = 0; i < input.length; i += 1) {
      const s = Math.max(-1, Math.min(1, input[i]));
      out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    return out;
  }
  const ratio = inputSampleRate / TARGET_SR;
  const newLen = Math.max(1, Math.floor(input.length / ratio));
  const out = new Int16Array(newLen);
  for (let i = 0; i < newLen; i += 1) {
    const idx = Math.min(input.length - 1, Math.floor(i * ratio));
    const s = Math.max(-1, Math.min(1, input[idx]));
    out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return out;
}

async function recordPcmBlob(durationMs: number): Promise<Blob> {
  // 关闭浏览器 NS，避免与服务端 DeepFilterNet 双重降噪损伤音色
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      channelCount: 1,
      echoCancellation: true,
      noiseSuppression: false,
      autoGainControl: true,
    },
  });
  const AudioCtx =
    window.AudioContext ||
    (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!AudioCtx) {
    stream.getTracks().forEach((t) => t.stop());
    throw new Error("AudioContext unsupported");
  }
  const ctx = new AudioCtx();
  const source = ctx.createMediaStreamSource(stream);
  const processor = ctx.createScriptProcessor(4096, 1, 1);
  const chunks: Int16Array[] = [];
  processor.onaudioprocess = (ev) => {
    const input = ev.inputBuffer.getChannelData(0);
    chunks.push(floatTo16BitPCM(input, ctx.sampleRate));
  };
  source.connect(processor);
  processor.connect(ctx.destination);
  await new Promise((r) => window.setTimeout(r, durationMs));
  processor.disconnect();
  source.disconnect();
  await ctx.close();
  stream.getTracks().forEach((t) => t.stop());
  const total = chunks.reduce((n, c) => n + c.length, 0);
  const merged = new Int16Array(total);
  let offset = 0;
  for (const c of chunks) {
    merged.set(c, offset);
    offset += c.length;
  }
  return new Blob([merged.buffer], { type: "application/octet-stream" });
}

export default function VoiceprintManagerPanel({ onChanged }: { onChanged?: () => void }) {
  const intl = useIntl();
  const [items, setItems] = useState<VoiceprintProfile[]>([]);
  const [loading, setLoading] = useState(false);
  const [enrollingId, setEnrollingId] = useState<string | null>(null);
  const [enrollOpen, setEnrollOpen] = useState(false);
  const [enrollTarget, setEnrollTarget] = useState<VoiceprintProfile | null>(null);
  const [deviceHint, setDeviceHint] = useState<string>("laptop");
  const [envHint, setEnvHint] = useState<string>("office");
  const [editOpen, setEditOpen] = useState(false);
  const [editing, setEditing] = useState<VoiceprintProfile | null>(null);
  const [form] = Form.useForm<{ display_name: string; description?: string }>();
  const busyRef = useRef(false);
  const onChangedRef = useRef(onChanged);
  onChangedRef.current = onChanged;

  const notifyChanged = useCallback(() => {
    onChangedRef.current?.();
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await AgentController.listVoiceprints();
      setItems(data.items ?? []);
    } catch (err) {
      message.error(
        intl.formatMessage(
          { id: "aiAssistant.voiceprint.loadFailed" },
          { error: err instanceof Error ? err.message : String(err) },
        ),
      );
    } finally {
      setLoading(false);
    }
  }, [intl]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const openCreate = () => {
    setEditing(null);
    form.setFieldsValue({ display_name: "", description: "" });
    setEditOpen(true);
  };

  const openEdit = (row: VoiceprintProfile) => {
    setEditing(row);
    form.setFieldsValue({
      display_name: row.display_name,
      description: row.description || "",
    });
    setEditOpen(true);
  };

  const saveProfile = async () => {
    const values = await form.validateFields();
    try {
      if (editing) {
        await AgentController.updateVoiceprint(editing.id, values);
        message.success(intl.formatMessage({ id: "aiAssistant.voiceprint.updated" }));
      } else {
        await AgentController.createVoiceprint(values);
        message.success(intl.formatMessage({ id: "aiAssistant.voiceprint.created" }));
      }
      setEditOpen(false);
      await refresh();
      notifyChanged();
    } catch (err) {
      message.error(
        intl.formatMessage(
          { id: "aiAssistant.voiceprint.saveFailed" },
          { error: err instanceof Error ? err.message : String(err) },
        ),
      );
    }
  };

  const removeProfile = async (id: string) => {
    try {
      await AgentController.deleteVoiceprint(id);
      message.success(intl.formatMessage({ id: "aiAssistant.voiceprint.deleted" }));
      await refresh();
      notifyChanged();
    } catch (err) {
      message.error(
        intl.formatMessage(
          { id: "aiAssistant.voiceprint.deleteFailed" },
          { error: err instanceof Error ? err.message : String(err) },
        ),
      );
    }
  };

  const openEnroll = (row: VoiceprintProfile) => {
    setEnrollTarget(row);
    setDeviceHint("laptop");
    setEnvHint("office");
    setEnrollOpen(true);
  };

  const enrollOne = async () => {
    if (!enrollTarget || busyRef.current) return;
    const max = ENROLL_MAX_DEFAULT;
    if (enrollTarget.sample_count >= max) {
      message.warning(
        intl.formatMessage({ id: "aiAssistant.voiceprint.enrollMaxReached" }, { max }),
      );
      return;
    }
    busyRef.current = true;
    setEnrollingId(enrollTarget.id);
    const next = enrollTarget.sample_count + 1;
    const min = enrollTarget.enroll_min ?? ENROLL_MIN_DEFAULT;
    const hide = message.loading(
      intl.formatMessage(
        { id: "aiAssistant.voiceprint.enrollingProgress" },
        { current: next, min, seconds: Math.round(ENROLL_MS / 1000) },
      ),
      0,
    );
    try {
      const blob = await recordPcmBlob(ENROLL_MS);
      const updated = await AgentController.enrollVoiceprint(enrollTarget.id, blob, {
        sampleRate: TARGET_SR,
        deviceHint,
        envHint,
      });
      hide();
      setEnrollTarget(updated);
      message.success(
        updated.enrolled
          ? intl.formatMessage({ id: "aiAssistant.voiceprint.enrollOk" })
          : intl.formatMessage(
              { id: "aiAssistant.voiceprint.enrollPartial" },
              { count: updated.sample_count, min: updated.enroll_min ?? min },
            ),
      );
      await refresh();
      notifyChanged();
      if (updated.enrolled && updated.sample_count >= max) {
        setEnrollOpen(false);
      }
    } catch (err) {
      hide();
      message.error(
        intl.formatMessage(
          { id: "aiAssistant.voiceprint.enrollFailed" },
          { error: err instanceof Error ? err.message : String(err) },
        ),
      );
    } finally {
      setEnrollingId(null);
      busyRef.current = false;
    }
  };

  return (
    <>
      <Space style={{ marginBottom: 12 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          {intl.formatMessage({ id: "aiAssistant.voiceprint.add" })}
        </Button>
        <Button onClick={() => void refresh()} loading={loading}>
          {intl.formatMessage({ id: "aiAssistant.voiceprint.refresh" })}
        </Button>
      </Space>
      <Table
        rowKey="id"
        size="small"
        loading={loading}
        dataSource={items}
        locale={{
          emptyText: (
            <Empty
              description={intl.formatMessage({
                id: "aiAssistant.voiceprint.empty",
              })}
            />
          ),
        }}
        pagination={false}
        columns={[
          {
            title: intl.formatMessage({
              id: "aiAssistant.voiceprint.name",
            }),
            dataIndex: "display_name",
          },
          {
            title: intl.formatMessage({
              id: "aiAssistant.voiceprint.desc",
            }),
            dataIndex: "description",
            ellipsis: true,
          },
          {
            title: intl.formatMessage({
              id: "aiAssistant.voiceprint.status",
            }),
            width: 140,
            render: (_, row) =>
              row.enrolled ? (
                <Tag color="success">
                  {intl.formatMessage(
                    { id: "aiAssistant.voiceprint.enrolled" },
                    { count: row.sample_count },
                  )}
                </Tag>
              ) : (
                <Tag>
                  {intl.formatMessage(
                    { id: "aiAssistant.voiceprint.enrollProgress" },
                    {
                      count: row.sample_count,
                      min: row.enroll_min ?? ENROLL_MIN_DEFAULT,
                    },
                  )}
                </Tag>
              ),
          },
          {
            title: intl.formatMessage({
              id: "aiAssistant.voiceprint.actions",
            }),
            width: 180,
            render: (_, row) => (
              <Space>
                <Tooltip
                  title={intl.formatMessage({
                    id: "aiAssistant.voiceprint.enrollTip",
                  })}
                >
                  <Button
                    size="small"
                    icon={<AudioOutlined />}
                    loading={enrollingId === row.id}
                    onClick={() => openEnroll(row)}
                  />
                </Tooltip>
                <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(row)} />
                <Popconfirm
                  title={intl.formatMessage({
                    id: "aiAssistant.voiceprint.deleteConfirm",
                  })}
                  onConfirm={() => void removeProfile(row.id)}
                >
                  <Button size="small" danger icon={<DeleteOutlined />} />
                </Popconfirm>
              </Space>
            ),
          },
        ]}
      />

      <Modal
        open={editOpen}
        title={intl.formatMessage({
          id: editing ? "aiAssistant.voiceprint.editTitle" : "aiAssistant.voiceprint.addTitle",
        })}
        onCancel={() => setEditOpen(false)}
        onOk={() => void saveProfile()}
        destroyOnHidden
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="display_name"
            label={intl.formatMessage({ id: "aiAssistant.voiceprint.name" })}
            rules={[{ required: true, message: "必填" }]}
          >
            <Input maxLength={64} />
          </Form.Item>
          <Form.Item
            name="description"
            label={intl.formatMessage({ id: "aiAssistant.voiceprint.desc" })}
          >
            <Input.TextArea maxLength={200} rows={2} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        open={enrollOpen}
        title={intl.formatMessage(
          { id: "aiAssistant.voiceprint.enrollWizardTitle" },
          { name: enrollTarget?.display_name ?? "" },
        )}
        onCancel={() => setEnrollOpen(false)}
        footer={null}
        destroyOnHidden
      >
        {enrollTarget ? (
          <Space direction="vertical" style={{ width: "100%" }} size="middle">
            <Progress
              percent={Math.min(
                100,
                Math.round(
                  (enrollTarget.sample_count / (enrollTarget.enroll_min ?? ENROLL_MIN_DEFAULT)) *
                    100,
                ),
              )}
              format={() =>
                `${enrollTarget.sample_count} / ${enrollTarget.enroll_min ?? ENROLL_MIN_DEFAULT}`
              }
            />
            <div>{intl.formatMessage({ id: "aiAssistant.voiceprint.enrollWizardHint" })}</div>
            <Form layout="vertical">
              <Form.Item label={intl.formatMessage({ id: "aiAssistant.voiceprint.deviceHint" })}>
                <Select
                  value={deviceHint}
                  onChange={setDeviceHint}
                  options={[
                    {
                      value: "headset",
                      label: intl.formatMessage({ id: "aiAssistant.voiceprint.device.headset" }),
                    },
                    {
                      value: "laptop",
                      label: intl.formatMessage({ id: "aiAssistant.voiceprint.device.laptop" }),
                    },
                    {
                      value: "phone",
                      label: intl.formatMessage({ id: "aiAssistant.voiceprint.device.phone" }),
                    },
                    {
                      value: "meeting",
                      label: intl.formatMessage({ id: "aiAssistant.voiceprint.device.meeting" }),
                    },
                    {
                      value: "other",
                      label: intl.formatMessage({ id: "aiAssistant.voiceprint.device.other" }),
                    },
                  ]}
                />
              </Form.Item>
              <Form.Item label={intl.formatMessage({ id: "aiAssistant.voiceprint.envHint" })}>
                <Select
                  value={envHint}
                  onChange={setEnvHint}
                  options={[
                    {
                      value: "office",
                      label: intl.formatMessage({ id: "aiAssistant.voiceprint.env.office" }),
                    },
                    {
                      value: "home",
                      label: intl.formatMessage({ id: "aiAssistant.voiceprint.env.home" }),
                    },
                    {
                      value: "outdoor",
                      label: intl.formatMessage({ id: "aiAssistant.voiceprint.env.outdoor" }),
                    },
                    {
                      value: "other",
                      label: intl.formatMessage({ id: "aiAssistant.voiceprint.env.other" }),
                    },
                  ]}
                />
              </Form.Item>
            </Form>
            <Button
              type="primary"
              icon={<AudioOutlined />}
              loading={enrollingId === enrollTarget.id}
              disabled={enrollTarget.sample_count >= ENROLL_MAX_DEFAULT}
              onClick={() => void enrollOne()}
              block
            >
              {intl.formatMessage({ id: "aiAssistant.voiceprint.enrollRecordNext" })}
            </Button>
          </Space>
        ) : null}
      </Modal>
    </>
  );
}
