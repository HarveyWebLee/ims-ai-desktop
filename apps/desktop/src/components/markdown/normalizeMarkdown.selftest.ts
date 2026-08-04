/**
 * normalizeMarkdown 单元校验（无 vitest 时用 node 直接跑）
 * 运行：cd apps/desktop && pnpm exec tsx src/components/markdown/normalizeMarkdown.selftest.ts
 */
import {
  ensureBlankLineBeforeTables,
  normalizeMarkdown,
  repairCollapsedGfmTables,
} from "./normalizeMarkdown";

function assert(cond: unknown, msg: string): void {
  if (!cond) throw new Error(msg);
}

const collapsed =
  "| 功能 | 历史数据导出模板 | 历史数据导出任务管理 | |------------------|-----------------------------------|-----------------------------------| | 角色定位 | 配置工具 | 执行监控 |";

const repaired = repairCollapsedGfmTables(collapsed);
assert(repaired.includes("\n"), "collapsed table should gain newlines");
assert(repaired.split("\n").length >= 3, `expected >=3 rows, got:\n${repaired}`);
assert(!repaired.includes("| |---"), "separator should be on its own line context");

const withPara = normalizeMarkdown(`说明如下：\n| A | B |\n|---|---|\n| 1 | 2 |`);
assert(withPara.includes("说明如下：\n\n| A | B |"), `blank line before table:\n${withPara}`);

const blanked = ensureBlankLineBeforeTables("| A | B |\n|---|---|\n| 1 | 2 |");
assert(!blanked.startsWith("\n"), "table at start needs no leading blank");

const crlf = normalizeMarkdown("| A | B |\r\n|---|---|\r\n| 1 | 2 |");
assert(!crlf.includes("\r"), "CRLF normalized");

console.log("normalizeMarkdown.selftest: ok"); // eslint-disable-line no-console
