import { useState } from "react";
import { ConfigProvider, App as AntApp } from "antd";
import zhCN from "antd/locale/zh_CN";
import { getToken } from "@ims/desktop-api";
import { DesktopIntlProvider } from "./shims/umijs-max";
import LoginPage from "./pages/LoginPage";
import DesktopChatApp from "./components/AiAssistant/DesktopChatApp";
import "antd/dist/reset.css";

const brandTheme = {
  token: {
    colorPrimary: "#479434",
    colorInfo: "#479434",
    colorLink: "#3a7a2c",
    borderRadius: 10,
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif',
  },
  components: {
    Button: {
      primaryShadow: "0 4px 12px rgba(71, 148, 52, 0.25)",
    },
    Layout: {
      headerBg: "#ffffff",
      bodyBg: "#f4f6f8",
    },
  },
};

export default function RootApp() {
  const [authed, setAuthed] = useState(() => !!getToken());

  return (
    <ConfigProvider locale={zhCN} theme={brandTheme}>
      <AntApp>
        <DesktopIntlProvider>
          {authed ? <DesktopChatApp /> : <LoginPage onSuccess={() => setAuthed(true)} />}
        </DesktopIntlProvider>
      </AntApp>
    </ConfigProvider>
  );
}
