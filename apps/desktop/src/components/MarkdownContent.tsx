/**
 * Markdown 渲染（GFM：表格 / 删除线 / 任务列表 / 自动链接）
 *
 * - remark-gfm：管道表等
 * - normalizeMarkdown：修复模型把表格挤成一行等常见问题
 * - 外链 target=_blank（Electron 走 openExternal）；禁 javascript: URL
 */
import { memo, useMemo } from "react";
import ReactMarkdown, { defaultUrlTransform } from "react-markdown";
import remarkGfm from "remark-gfm";
import { markdownComponents } from "./markdown/markdownComponents";
import { normalizeMarkdown } from "./markdown/normalizeMarkdown";

const REMARK_PLUGINS = [remarkGfm];

function urlTransform(url: string): string {
  const trimmed = (url || "").trim();
  if (!trimmed) return "";
  // 允许 http(s) / mailto / 相对锚点；拦截 javascript: 等
  if (/^(javascript|vbscript|file):/i.test(trimmed)) return "";
  if (/^data:/i.test(trimmed) && !/^data:image\//i.test(trimmed)) return "";
  return defaultUrlTransform(trimmed);
}

function MarkdownContent({
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
  const normalized = useMemo(() => normalizeMarkdown(content || ""), [content]);

  return (
    <div className={className ? `markdown-body ${className}` : "markdown-body"}>
      <ReactMarkdown
        remarkPlugins={REMARK_PLUGINS}
        components={markdownComponents}
        urlTransform={urlTransform}
      >
        {normalized}
      </ReactMarkdown>
    </div>
  );
}

export default memo(MarkdownContent);
