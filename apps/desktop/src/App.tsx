import { useState, type ReactNode } from "react";
import { ConfigProvider, App as AntApp } from "antd";
import zhCN from "antd/locale/zh_CN";
import { IntlProvider } from "react-intl";
import dayjs from "dayjs";
import "dayjs/locale/zh-cn";
import { getToken } from "@ims/desktop-api";
import LoginPage from "./pages/LoginPage";
import SettingsPage from "./pages/SettingsPage";
import DesktopChatApp from "./components/AiAssistant/DesktopChatApp";
import AntdAppBridge from "./antd/AntdAppBridge";
import aiAssistantZhCN from "./locales/ai_assistant/zh-CN";
import aiAssistantEnUS from "./locales/ai_assistant/en-US";
import "antd/dist/reset.css";

dayjs.locale("zh-cn");

type AppPage = "chat" | "settings";

const messages: Record<string, Record<string, string>> = {
  "zh-CN": flattenMessages({ aiAssistant: aiAssistantZhCN }),
  "en-US": flattenMessages({ aiAssistant: aiAssistantEnUS }),
};

function flattenMessages(nested: Record<string, unknown>, prefix = ""): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [key, value] of Object.entries(nested)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (value && typeof value === "object" && !Array.isArray(value)) {
      Object.assign(out, flattenMessages(value as Record<string, unknown>, path));
    } else if (typeof value === "string") {
      out[path] = value;
    }
  }
  return out;
}

function DesktopIntlProvider({
  children,
  locale = "zh-CN",
}: {
  children: ReactNode;
  locale?: string;
}) {
  const loc = locale in messages ? locale : "zh-CN";
  return (
    <IntlProvider locale={loc} messages={messages[loc]} onError={() => undefined}>
      {children}
    </IntlProvider>
  );
}

export default function RootApp() {
  const [authed, setAuthed] = useState(() => !!getToken());
  const [page, setPage] = useState<AppPage>("chat");

  // 不传 theme：使用 antd 6 默认 Design Token / CSS Variables
  return (
    <ConfigProvider locale={zhCN}>
      <AntApp
        style={{ height: "100%" }}
        message={{ maxCount: 3, duration: 3 }}
        notification={{ placement: "topRight", maxCount: 3 }}
      >
        <AntdAppBridge />
        <DesktopIntlProvider>
          {!authed ? (
            <LoginPage onSuccess={() => setAuthed(true)} />
          ) : page === "settings" ? (
            <SettingsPage onBack={() => setPage("chat")} />
          ) : (
            <DesktopChatApp onOpenSettings={() => setPage("settings")} />
          )}
        </DesktopIntlProvider>
      </AntApp>
    </ConfigProvider>
  );
}
