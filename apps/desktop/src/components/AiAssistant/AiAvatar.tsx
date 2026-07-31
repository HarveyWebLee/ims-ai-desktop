/**
 * AI 助手标识：简洁星芒图形，替代 RobotOutlined
 */
import { theme } from "antd";
import styles from "./index.module.less";

/** 四角星 + 副星点，path 使用直线确保各端渲染一致 */
export function AiMark({ size = 16, className }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="currentColor"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden
      focusable="false"
    >
      <path d="M12 2.2 14.35 9.15 21.5 11.5 14.35 13.85 12 20.8 9.65 13.85 2.5 11.5 9.65 9.15Z" />
      <circle cx="19.4" cy="5" r="1.4" opacity="0.55" />
      <circle cx="5" cy="17.8" r="1.1" opacity="0.4" />
    </svg>
  );
}

/** 聊天气泡旁 / 空态用的 AI 头像 */
export function AiAvatar({ size = 32, className }: { size?: number; className?: string }) {
  const { token } = theme.useToken();
  const iconSize = Math.max(12, Math.round(size * 0.48));
  const radius = Math.round(size * 0.28);

  return (
    <span
      className={[styles.aiAvatar, className].filter(Boolean).join(" ")}
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
        width: size,
        height: size,
        borderRadius: radius,
        background: token.colorPrimary,
        color: "#fff",
        boxShadow: `0 2px 8px ${token.colorPrimary}38`,
      }}
      aria-hidden
    >
      <AiMark size={iconSize} />
    </span>
  );
}
