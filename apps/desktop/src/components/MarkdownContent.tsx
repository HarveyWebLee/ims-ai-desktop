/**
 * Markdown 简易渲染（替代 App MarkdownContent）
 */
import ReactMarkdown from "react-markdown";

export default function MarkdownContent({
  content,
  className,
}: {
  content?: string;
  className?: string;
  /** 兼容旧调用方；桌面端 M1 不区分紧凑态 */
  compact?: boolean;
  /** 兼容旧调用方；流式态由外层 Spin 提示 */
  streaming?: boolean;
}) {
  return (
    <div className={className ? `markdown-body ${className}` : "markdown-body"}>
      <ReactMarkdown>{content || ""}</ReactMarkdown>
    </div>
  );
}
