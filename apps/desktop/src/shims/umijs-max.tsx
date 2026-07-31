/**
 * @umijs/max 桌面端 shim：react-intl + 假路由
 */
import { createContext, type ReactNode } from "react";
import { IntlProvider, useIntl as useReactIntl, type IntlShape } from "react-intl";
import zhCN from "../locales/ai_assistant/zh-CN";
import enUS from "../locales/ai_assistant/en-US";

export type { IntlShape };

const messages: Record<string, Record<string, string>> = {
  "zh-CN": flattenMessages({ aiAssistant: zhCN }),
  "en-US": flattenMessages({ aiAssistant: enUS }),
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

const LocaleCtx = createContext("zh-CN");

export function DesktopIntlProvider({
  children,
  locale = "zh-CN",
}: {
  children: ReactNode;
  locale?: string;
}) {
  const loc = locale in messages ? locale : "zh-CN";
  return (
    <LocaleCtx.Provider value={loc}>
      <IntlProvider locale={loc} messages={messages[loc]} onError={() => undefined}>
        {children}
      </IntlProvider>
    </LocaleCtx.Provider>
  );
}

export function useIntl(): IntlShape {
  return useReactIntl() as IntlShape;
}

export function getLocale(): string {
  return "zh-CN";
}

export function getIntl(): IntlShape {
  throw new Error("getIntl 仅在渲染树内通过 useIntl 使用");
}

export function useLocation() {
  return { pathname: "/", search: "", hash: "", state: null };
}

export const history = {
  push: (_path: string) => {
    console.warn("[desktop] history.push skipped:", _path);
  },
  replace: (_path: string) => {
    console.warn("[desktop] history.replace skipped:", _path);
  },
};

export const SelectLang = () => null;
