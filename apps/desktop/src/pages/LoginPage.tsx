/**
 * 桌面端登录页
 */
import { useState } from "react";
import { App, Button, Card, Form, Input, Typography, theme } from "antd";
import { RobotOutlined } from "@ant-design/icons";
import { login } from "@ims/desktop-api";

const { Title, Text } = Typography;

export default function LoginPage({ onSuccess }: { onSuccess: () => void }) {
  const [loading, setLoading] = useState(false);
  const { message } = App.useApp();
  const { token } = theme.useToken();

  const handleFinish = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      await login(values.username, values.password);
      message.success("登录成功");
      onSuccess();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "登录失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "linear-gradient(145deg, #0f172a 0%, #1e3a5f 45%, #0c4a6e 100%)",
        padding: 24,
      }}
    >
      <Card style={{ width: 400, maxWidth: "100%" }}>
        <div style={{ textAlign: "center", marginBottom: 24 }}>
          <RobotOutlined style={{ fontSize: 40, color: token.colorPrimary }} />
          <Title level={3} style={{ marginTop: 12, marginBottom: 4 }}>
            IMS AI 助手
          </Title>
          <Text type="secondary">桌面端 · 连接平台与 Agent 服务</Text>
        </div>
        <Form layout="vertical" onFinish={handleFinish} autoComplete="on">
          <Form.Item
            name="username"
            label="用户名"
            rules={[{ required: true, message: "请输入用户名" }]}
          >
            <Input placeholder="root" autoComplete="username" />
          </Form.Item>
          <Form.Item
            name="password"
            label="密码"
            rules={[{ required: true, message: "请输入密码" }]}
          >
            <Input.Password placeholder="密码" autoComplete="current-password" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>
            登录
          </Button>
        </Form>
      </Card>
    </div>
  );
}
