#!/usr/bin/env node
/**
 * 拦截高风险 shell 命令，避免误伤仓库。
 */
import { readFileSync } from "fs";

const input = JSON.parse(readFileSync(0, "utf-8"));
const command = String(input?.command || "").trim();

const denyRules = [
  {
    pattern: /\bgit\s+reset\s+--hard\b/,
    msg: "禁止 git reset --hard，可能丢失本地改动",
  },
  {
    pattern: /\bgit\s+clean\s+-[a-z]*f/,
    msg: "禁止 git clean -f，可能删除未跟踪文件",
  },
  {
    pattern: /\bgit\s+push\b.*(--force|-f)\b/,
    msg: "禁止强推，请使用安全推送流程",
  },
  { pattern: /\brm\s+-rf\s+\/(?!tmp)/, msg: "禁止删除系统根目录" },
];

for (const rule of denyRules) {
  if (rule.pattern.test(command)) {
    process.stdout.write(
      JSON.stringify({
        permission: "deny",
        user_message: rule.msg,
        agent_message: `危险命令已拦截: ${command}`,
      }),
    );
    process.exit(0);
  }
}

process.stdout.write(JSON.stringify({ permission: "allow" }));
