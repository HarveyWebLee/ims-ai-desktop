/**
 * 渲染前规范化：修复模型常见的「表格挤一行」等 GFM 问题。
 */

/** 分隔行片段：|---| 或 |:---| 等 */
const TABLE_SEP_CHUNK = String.raw`(?:[\t ]*:?-{3,}:?[\t ]*\|)+`;

/**
 * 将挤在同一物理行内的 GFM 表拆成多行。
 * 例：`| a | b | |---|---| | 1 | 2 |` → 标准三行表。
 */
export function repairCollapsedGfmTables(text: string): string {
  return text
    .split("\n")
    .map((line) => {
      if (!line.includes("|") || line.split("|").length < 4) {
        return line;
      }
      if (!new RegExp(`\\|${TABLE_SEP_CHUNK}`).test(line)) {
        return line;
      }
      let s = line;
      // 数据行 → 分隔行
      s = s.replace(
        new RegExp(`(\\|(?:[^\\n|]+\\|)+)[\\t ]*(?=\\|${TABLE_SEP_CHUNK})`, "g"),
        "$1\n",
      );
      // 分隔行 → 后续行
      s = s.replace(new RegExp(`(\\|${TABLE_SEP_CHUNK})[\\t ]*(?=\\|)`, "g"), "$1\n");
      // 连续数据行：`| a | | b |`
      s = s.replace(/(\|(?:[^\n|]+\|)+)[\t ]*(?=\|(?![-\t :|]*\|)[^\n|]+\|)/g, "$1\n");
      return s;
    })
    .join("\n");
}

/** 表格块前补空行，避免紧贴普通段落后表头解析不稳定 */
export function ensureBlankLineBeforeTables(text: string): string {
  const lines = text.split("\n");
  const out: string[] = [];
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i] ?? "";
    const next = lines[i + 1];
    const isTableStart = /^\|.+\|\s*$/.test(line) && next != null && /^\|[\t ]*:?-{3,}/.test(next);
    const prev = out.length > 0 ? out[out.length - 1] : "";
    if (isTableStart && prev != null && prev.trim() !== "" && !prev.trimStart().startsWith("|")) {
      out.push("");
    }
    out.push(line);
  }
  return out.join("\n");
}

/**
 * 统一换行并做轻量 GFM 修复。
 */
export function normalizeMarkdown(content: string): string {
  if (!content) return "";
  let text = content.replace(/\r\n?/g, "\n");
  // 去掉行尾多余空白；保留恰好 2 个尾随空格（Markdown 硬换行）
  text = text
    .split("\n")
    .map((line) => {
      if (/\S {2}$/.test(line)) return line;
      return line.replace(/[ \t]+$/g, "");
    })
    .join("\n");
  text = repairCollapsedGfmTables(text);
  text = ensureBlankLineBeforeTables(text);
  return text;
}
