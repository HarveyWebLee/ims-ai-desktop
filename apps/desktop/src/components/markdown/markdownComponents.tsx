/**
 * react-markdown 自定义节点：外链安全打开、表格横向滚动、图片限宽。
 */
import type { Components } from "react-markdown";
import type { DetailedHTMLProps, ImgHTMLAttributes } from "react";

function isSafeHttpUrl(href: string | undefined): boolean {
  if (!href) return false;
  try {
    const u = new URL(href, "https://placeholder.local");
    return u.protocol === "http:" || u.protocol === "https:" || u.protocol === "mailto:";
  } catch {
    return false;
  }
}

export const markdownComponents: Components = {
  a({ href, children, ...props }) {
    const safe = isSafeHttpUrl(href) ? href : undefined;
    return (
      <a
        {...props}
        href={safe}
        target="_blank"
        rel="noreferrer noopener"
        onClick={(e) => {
          // Electron：target=_blank 由主进程 setWindowOpenHandler → openExternal
          if (!safe) e.preventDefault();
        }}
      >
        {children}
      </a>
    );
  },
  img({
    src,
    alt,
    ...props
  }: DetailedHTMLProps<ImgHTMLAttributes<HTMLImageElement>, HTMLImageElement>) {
    const safeSrc =
      typeof src === "string" &&
      (src.startsWith("http://") || src.startsWith("https://") || src.startsWith("data:image/"))
        ? src
        : undefined;
    if (!safeSrc) return null;
    return <img {...props} src={safeSrc} alt={alt ?? ""} loading="lazy" />;
  },
  table({ children, ...props }) {
    return (
      <div className="markdown-table-wrap">
        <table {...props}>{children}</table>
      </div>
    );
  },
};
